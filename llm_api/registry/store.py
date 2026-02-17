"""Database-backed model registry."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from sqlalchemy import select, or_

from llm_api.api.schemas import ModelCapabilities, ModelInfo, ModelSource
from llm_api.config import get_settings
from llm_api.db.database import get_db_session
from llm_api.db.models import ModelRecord

logger = logging.getLogger(__name__)


def _model_record_to_info(record: ModelRecord) -> ModelInfo:
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
    if record.max_context_tokens or record.output_formats or record.hardware_requirements:
        capabilities = ModelCapabilities(
            max_context_tokens=record.max_context_tokens,
            output_formats=record.output_formats or [],
            hardware_requirements=record.hardware_requirements or [],
        )
    
    is_default = record.id in {
        settings.default_model,
        settings.default_image_model,
        settings.default_3d_model,
    }

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
    
    return record


@dataclass
class ModelRegistry:
    """Database-backed model registry."""
    ready: bool = False
    _cache: Dict[str, ModelInfo] = field(default_factory=dict)
    _cache_time: Optional[datetime] = None
    _cache_ttl_seconds: int = 30  # Cache for 30 seconds

    def load_defaults(self) -> None:
        """Initialize the registry and ensure default models exist for each modality."""
        settings = get_settings()
        models_dir = Path(settings.model_path)

        defaults = [
            ModelInfo(
                id=settings.default_model,
                name="Llama 3.1 8B Instruct",
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
        """Remove auto-discovered local models that are not in the defaults list."""
        with get_db_session() as db:
            query = (
                select(ModelRecord)
                .where(ModelRecord.id.notin_(allowed_ids))
                .where(or_(ModelRecord.source_type.is_(None), ModelRecord.source_type == "local"))
            )
            records = db.execute(query).scalars().all()
            for record in records:
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

    def list_models(self, modality: Optional[str] = None) -> List[ModelInfo]:
        """List all registered models, optionally filtered by modality."""
        with get_db_session() as db:
            query = select(ModelRecord)
            if modality:
                query = query.where(ModelRecord.modality == modality)
            
            records = db.execute(query).scalars().all()
            return [_model_record_to_info(r) for r in records]

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        with get_db_session() as db:
            record = db.get(ModelRecord, model_id)
            if record:
                # Update last_used_at
                record.last_used_at = datetime.now(timezone.utc)
                db.add(record)
                return _model_record_to_info(record)
            return None

    def get_model_by_local_path(self, local_path: str) -> Optional[ModelInfo]:
        """Get a model by its local file path."""
        with get_db_session() as db:
            query = select(ModelRecord).where(ModelRecord.local_path == local_path)
            record = db.execute(query).scalars().first()
            if record:
                return _model_record_to_info(record)
            return None

    def add_model(self, model: ModelInfo) -> ModelInfo:
        """Add or update a model in the registry."""
        if not model.id:
            model.id = str(uuid.uuid4())
        
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
            return _model_record_to_info(record)

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
    return _registry
