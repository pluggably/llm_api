"""Database-backed model registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from sqlalchemy import select, or_

from llm_api.api.schemas import ModelCapabilities, ModelInfo, ModelSource
from llm_api.config import get_settings
from llm_api.db.database import get_db_session
from llm_api.db.models import DefaultModelRecord, ModelRecord

logger = logging.getLogger(__name__)


def _model_record_to_info(record: ModelRecord, default_ids: set[str]) -> ModelInfo:
    """Convert a database record to a ModelInfo schema."""
    settings = get_settings()
    source = None
    if record.source_type and record.source_uri:
        # Cast to the expected Literal type
        source_type: Literal["huggingface", "url", "local"] = (
            record.source_type if record.source_type in ("huggingface", "url", "local") 
            else "local"
        )  # type: ignore[assignment]
        source = ModelSource(type=source_type, uri=record.source_uri)
    
    capabilities = None
    if (record.max_context_tokens or record.output_formats or record.hardware_requirements
            or record.image_input_max_edge or record.image_input_max_pixels
            or record.image_input_formats):
        capabilities = ModelCapabilities(
            max_context_tokens=record.max_context_tokens,
            output_formats=record.output_formats or [],
            hardware_requirements=record.hardware_requirements or [],
            image_input_max_edge=record.image_input_max_edge,
            image_input_max_pixels=record.image_input_max_pixels,
            image_input_formats=record.image_input_formats,
        )
    
    is_default = record.id in default_ids

    return ModelInfo(
        id=record.id,
        name=record.name,
        version=record.version,
        modality=record.modality,  # type: ignore[arg-type]
        provider=record.provider,
        status=record.status,  # type: ignore[arg-type]
        local_path=record.local_path,
        size_bytes=record.size_bytes,
        source=source,
        capabilities=capabilities,
        last_used_at=record.last_used_at,
        is_default=is_default,
    )


def _resolve_local_path(models_dir: Path, relative_path: str, require_config: bool = False) -> Optional[str]:
    candidate = models_dir / relative_path
    if not candidate.exists():
        return None
    if require_config and not (candidate / "config.json").exists():
        return None
    return relative_path


def _model_info_to_record(model: ModelInfo, existing: Optional[ModelRecord] = None) -> ModelRecord:
    """Convert a ModelInfo schema to a database record."""
    if existing:
        record = existing
    else:
        record = ModelRecord(id=model.id)
    
    record.name = model.name
    record.version = model.version or "latest"
    record.modality = model.modality
    record.provider = model.provider
    record.status = model.status or "available"
    record.local_path = model.local_path
    record.size_bytes = model.size_bytes
    
    if model.source:
        record.source_type = model.source.type
        record.source_uri = model.source.uri
    
    if model.capabilities:
        record.max_context_tokens = model.capabilities.max_context_tokens
        record.output_formats = model.capabilities.output_formats
        record.hardware_requirements = model.capabilities.hardware_requirements
        record.image_input_max_edge = model.capabilities.image_input_max_edge
        record.image_input_max_pixels = model.capabilities.image_input_max_pixels
        record.image_input_formats = model.capabilities.image_input_formats
    
    return record


@dataclass
class ModelRegistry:
    """Database-backed model registry."""
    ready: bool = False
    _cache: Dict[str, ModelInfo] = field(default_factory=dict)
    _cache_time: Optional[datetime] = None
    _cache_ttl_seconds: int = 30  # Cache for 30 seconds

    def _build_default_models(self) -> list[ModelInfo]:
        settings = get_settings()
        models_dir = Path(settings.model_path)
        return [
            ModelInfo(
                id=settings.default_model,
                name="Qwen 2.5 3B Instruct",
                version="latest",
                modality="text",
                provider="local",
                status="available",
                source=ModelSource(type="huggingface", uri=settings.default_model),
                local_path=_resolve_local_path(
                    models_dir,
                    f"hf/{settings.default_model.replace('/', '__')}",
                    require_config=True,
                ),
                capabilities=ModelCapabilities(
                    max_context_tokens=8192,
                    output_formats=["text"],
                    hardware_requirements=["CPU", "Metal", "CUDA"],
                ),
            ),
            ModelInfo(
                id=settings.default_image_model,
                name="SDXL Turbo",
                version="latest",
                modality="image",
                provider="local",
                status="available",
                source=ModelSource(type="huggingface", uri=settings.default_image_model),
                local_path=_resolve_local_path(models_dir, "sd_xl_turbo_1.0.safetensors"),
                capabilities=ModelCapabilities(
                    output_formats=["image"],
                    hardware_requirements=["CUDA", "Metal"],
                ),
            ),
            ModelInfo(
                id="stabilityai/stable-diffusion-xl-base-1.0",
                name="Stable Diffusion XL",
                version="latest",
                modality="image",
                provider="local",
                status="available",
                source=ModelSource(type="huggingface", uri="stabilityai/stable-diffusion-xl-base-1.0"),
                local_path=_resolve_local_path(models_dir, "sd_xl_base_1.0.safetensors"),
                capabilities=ModelCapabilities(
                    output_formats=["image"],
                    hardware_requirements=["CUDA", "Metal"],
                ),
            ),
            ModelInfo(
                id=settings.default_3d_model,
                name="Shap-E",
                version="latest",
                modality="3d",
                provider="local",
                status="available",
                source=ModelSource(type="huggingface", uri=settings.default_3d_model),
                capabilities=ModelCapabilities(
                    output_formats=["mesh"],
                    hardware_requirements=["CPU", "Metal", "CUDA"],
                ),
            ),
        ]

    def ensure_defaults_present(self) -> None:
        """Ensure default model rows exist without pruning user-added models."""
        for model in self._build_default_models():
            existing = self.get_model(model.id)
            if existing:
                continue
            self.add_model(model)

    def load_defaults(self) -> None:
        """Initialize the registry and ensure default models exist for each modality."""
        settings = get_settings()
        models_dir = Path(settings.model_path)
        defaults = self._build_default_models()

        allowed_ids = {m.id for m in defaults}
        for model in defaults:
            existing = self.get_model(model.id)
            if existing:
                if model.modality == "text" and model.source and model.source.type == "huggingface":
                    existing_local = (
                        _resolve_local_path(models_dir, existing.local_path, require_config=True)
                        if existing.local_path
                        else None
                    )
                else:
                    existing_local = existing.local_path

                model.local_path = existing_local or model.local_path
                model.status = existing.status
                model.size_bytes = existing.size_bytes or model.size_bytes
                model.source = existing.source or model.source
            self.add_model(model)

        self._prune_non_default_local_models(allowed_ids)
        self.ready = True

    def _prune_non_default_local_models(self, allowed_ids: set[str]) -> None:
        """Remove auto-discovered local models that are not in the defaults list,
        and deduplicate rows that share (name, modality) with a canonical default."""
        with get_db_session() as db:
            # Phase 1 – original prune: remove non-default local/untyped models
            query = (
                select(ModelRecord)
                .where(ModelRecord.id.notin_(allowed_ids))
                .where(or_(ModelRecord.source_type.is_(None), ModelRecord.source_type == "local"))
            )
            records = db.execute(query).scalars().all()
            for record in records:
                db.delete(record)

            # Phase 2 – deduplicate: remove rows with UUID-style IDs that
            # duplicate a canonical default (same name + modality, but wrong ID).
            # This cleans up damage from the empty-env-var bug where add_model()
            # assigned random UUIDs to models that should have had a fixed ID.
            canonical = {
                (r.name, r.modality)
                for r in db.execute(
                    select(ModelRecord).where(ModelRecord.id.in_(allowed_ids))
                ).scalars().all()
            }
            if canonical:
                dupes = (
                    db.execute(
                        select(ModelRecord).where(ModelRecord.id.notin_(allowed_ids))
                    )
                    .scalars()
                    .all()
                )
                for record in dupes:
                    if (record.name, record.modality) in canonical:
                        db.delete(record)
        self._invalidate_cache()

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if not self._cache_time:
            return False
        age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return age < self._cache_ttl_seconds

    def _invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._cache.clear()
        self._cache_time = None

    def _scan_local_models(self) -> None:
        """Scan the models directory for downloaded model files and register them."""
        settings = get_settings()
        models_dir = Path(settings.model_path)
        if not models_dir.exists():
            return
        
        # Get currently registered models and their local paths
        registered_models = self.list_models()
        registered_ids = {m.id for m in registered_models}
        registered_paths = {m.local_path for m in registered_models if m.local_path}
        
        # Scan for GGUF files (text models)
        for gguf_file in models_dir.glob("*.gguf"):
            filename = gguf_file.name
            model_id = gguf_file.stem  # e.g., "tinyllama-1.1b-chat-v1.0.Q4_K_M"
            
            # Skip if already registered (check by ID or local_path)
            if model_id in registered_ids or filename in registered_paths:
                continue
            
            # Parse model info from filename
            name = gguf_file.stem.replace(".Q4_K_M", "").replace(".Q8_0", "").replace(".Q5_K_M", "")
            size_bytes = gguf_file.stat().st_size
            
            # Determine quantization from filename
            quant = "unknown"
            for q in ["Q4_K_M", "Q8_0", "Q5_K_M", "Q4_0", "Q5_0", "Q6_K", "Q2_K", "Q3_K"]:
                if q in filename:
                    quant = q
                    break
            
            model = ModelInfo(
                id=model_id,
                name=name,
                version=quant,
                modality="text",
                provider="local",
                local_path=filename,
                size_bytes=size_bytes,
                status="available",
                source=ModelSource(type="local", uri=str(gguf_file)),
                capabilities=ModelCapabilities(
                    max_context_tokens=2048,
                    output_formats=["text"],
                    hardware_requirements=["CPU", "Metal", "CUDA"],
                ),
            )
            self.add_model(model)
            logger.info(f"Auto-registered model from file: {model_id}")

        # Scan for safetensors files (often image models like Stable Diffusion)
        for safetensor_file in models_dir.glob("*.safetensors"):
            filename = safetensor_file.name
            model_id = safetensor_file.stem
            
            # Skip if already registered
            if model_id in registered_ids or filename in registered_paths:
                continue
            
            size_bytes = safetensor_file.stat().st_size
            name = safetensor_file.stem.replace("_", " ").title()
            
            # Determine if this is likely a Stable Diffusion model
            is_sd = any(x in model_id.lower() for x in ["sd_", "sdxl", "stable", "diffusion"])
            if not is_sd:
                # Skip text HF shards; rely on registry-installed models with explicit local_path
                continue
            modality = "image"
            
            model = ModelInfo(
                id=model_id,
                name=name,
                version="1.0",
                modality=modality,
                provider="local",
                local_path=filename,
                size_bytes=size_bytes,
                status="available",
                source=ModelSource(type="local", uri=str(safetensor_file)),
                capabilities=ModelCapabilities(
                    output_formats=["image"],
                    hardware_requirements=["CUDA", "Metal"],
                ),
            )
            self.add_model(model)
            logger.info(f"Auto-registered model from file: {model_id}")

    def _get_default_ids(self) -> set[str]:
        """Get the set of default model IDs (DB overrides settings defaults)."""
        settings = get_settings()
        defaults_map: Dict[str, str] = {}
        with get_db_session() as db:
            rows = db.execute(select(DefaultModelRecord)).scalars().all()
            for row in rows:
                defaults_map[row.modality] = row.model_id

        if "text" not in defaults_map and settings.default_model:
            defaults_map["text"] = settings.default_model
        if "image" not in defaults_map and settings.default_image_model:
            defaults_map["image"] = settings.default_image_model
        if "3d" not in defaults_map and settings.default_3d_model:
            defaults_map["3d"] = settings.default_3d_model

        return set(defaults_map.values())

    def get_default_model_id(self, modality: str) -> Optional[str]:
        """Get default model ID for a modality, preferring DB over settings."""
        settings = get_settings()
        with get_db_session() as db:
            record = db.get(DefaultModelRecord, modality)
            if record:
                return record.model_id
        if modality == "image":
            return settings.default_image_model
        if modality == "3d":
            return settings.default_3d_model
        return settings.default_model

    def set_default_model(self, modality: str, model_id: str) -> None:
        """Set the default model for a modality (replaces any existing default)."""
        with get_db_session() as db:
            existing = db.get(DefaultModelRecord, modality)
            if existing:
                existing.model_id = model_id
                db.add(existing)
            else:
                db.add(DefaultModelRecord(modality=modality, model_id=model_id))

    def list_models(self, modality: Optional[str] = None) -> List[ModelInfo]:
        """List all registered models, optionally filtered by modality."""
        self.ensure_defaults_present()
        with get_db_session() as db:
            query = select(ModelRecord)
            if modality:
                query = query.where(ModelRecord.modality == modality)
            
            records = db.execute(query).scalars().all()
            default_ids = self._get_default_ids()
            return [_model_record_to_info(r, default_ids) for r in records]

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        with get_db_session() as db:
            record = db.get(ModelRecord, model_id)
            if record:
                # Update last_used_at
                record.last_used_at = datetime.now(timezone.utc)
                db.add(record)
                default_ids = self._get_default_ids()
                return _model_record_to_info(record, default_ids)
            return None

    def get_model_by_local_path(self, local_path: str) -> Optional[ModelInfo]:
        """Get a model by its local file path."""
        with get_db_session() as db:
            query = select(ModelRecord).where(ModelRecord.local_path == local_path)
            record = db.execute(query).scalars().first()
            if record:
                default_ids = self._get_default_ids()
                return _model_record_to_info(record, default_ids)
            return None

    def add_model(self, model: ModelInfo) -> ModelInfo:
        """Add or update a model in the registry.

        Raises:
            ValueError: If ``model.id`` is empty or None.  Every model must
                have an explicit, deterministic ID so that restarts do not
                create duplicates.
        """
        if not model.id:
            raise ValueError(
                f"Cannot register a model without an explicit ID "
                f"(name={model.name!r}, modality={model.modality!r}).  "
                f"Ensure default_model / default_image_model / default_3d_model "
                f"settings are not empty."
            )
        
        with get_db_session() as db:
            existing = db.get(ModelRecord, model.id)
            record = _model_info_to_record(model, existing)
            db.add(record)
        
        self._invalidate_cache()
        return model

    def update_model_status(
        self,
        model_id: str,
        status: Literal["available", "downloading", "failed", "disabled", "evicted"],
        error: str | None = None,
    ) -> None:
        """Update a model's status."""
        with get_db_session() as db:
            record = db.get(ModelRecord, model_id)
            if record:
                record.status = status
                db.add(record)
        
        self._invalidate_cache()

    def update_model(
        self,
        model_id: str,
        **kwargs,
    ) -> Optional[ModelInfo]:
        """Update model fields."""
        with get_db_session() as db:
            record = db.get(ModelRecord, model_id)
            if not record:
                return None
            
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            
            db.add(record)
            self._invalidate_cache()
            default_ids = self._get_default_ids()
            return _model_record_to_info(record, default_ids)

    def delete_model(self, model_id: str) -> bool:
        """Delete a model from the registry."""
        with get_db_session() as db:
            record = db.get(ModelRecord, model_id)
            if record:
                db.delete(record)
                self._invalidate_cache()
                return True
            return False

    def set_fallback(self, primary_id: str, fallback_id: str) -> None:
        """Set a fallback model for a primary model."""
        with get_db_session() as db:
            record = db.get(ModelRecord, primary_id)
            if record:
                record.fallback_model_id = fallback_id
                db.add(record)

    def get_fallback(self, primary_id: str) -> Optional[str]:
        """Get the fallback model ID for a primary model."""
        with get_db_session() as db:
            record = db.get(ModelRecord, primary_id)
            if record:
                return record.fallback_model_id
            return None

    def get_default_for_modality(self, modality: str) -> Optional[str]:
        """Get the first available model for a given modality.
        
        Returns the model ID of an available model matching the modality,
        preferring the most recently used one.
        """
        with get_db_session() as db:
            query = (
                select(ModelRecord)
                .where(ModelRecord.modality == modality)
                .where(ModelRecord.status == "available")
                .order_by(ModelRecord.last_used_at.desc().nulls_last())
                .limit(1)
            )
            record = db.execute(query).scalars().first()
            if record:
                return record.id
            return None

    def sync_with_storage(self, base_path: Path) -> None:
        """Sync registry with actual files on disk - mark missing files as evicted."""
        models = self.list_models()
        for model in models:
            if model.local_path:
                if not (base_path / model.local_path).exists():
                    self.update_model_status(model.id, "evicted")


_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get the singleton model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
        _registry.load_defaults()
        _registry._scan_local_models()
    return _registry
