from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from llm_api.api.schemas import ModelInfo
from llm_api.config import get_settings


@dataclass
class ModelRegistry:
    models: Dict[str, ModelInfo] = field(default_factory=dict)
    ready: bool = False
    fallbacks: Dict[str, str] = field(default_factory=dict)
    state_path: Optional[Path] = None

    def load_defaults(self) -> None:
        settings = get_settings()
        self.state_path = Path(settings.model_path) / "registry.json"
        default_model = ModelInfo(
            id=settings.default_model,
            name=settings.default_model,
            version="latest",
            modality="text",
            provider="local",
            status="available",
        )
        self.models[default_model.id] = default_model
        self.ready = True
        if settings.persist_state:
            self._load_state()

    def list_models(self, modality: Optional[str] = None) -> List[ModelInfo]:
        models = list(self.models.values())
        if modality:
            models = [m for m in models if m.modality == modality]
        return models

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        model = self.models.get(model_id)
        if model:
            model.last_used_at = datetime.now(timezone.utc)
            self.models[model_id] = model
        return model

    def add_model(self, model: ModelInfo) -> ModelInfo:
        if not model.id:
            model.id = str(uuid.uuid4())
        self.models[model.id] = model
        self._save_state()
        return model

    def update_model_status(
        self,
        model_id: str,
        status: Literal["available", "downloading", "failed", "disabled", "evicted"],
        error: str | None = None,
    ) -> None:
        model = self.models.get(model_id)
        if not model:
            return
        model.status = status
        self.models[model_id] = model
        self._save_state()

    def set_fallback(self, primary_id: str, fallback_id: str) -> None:
        self.fallbacks[primary_id] = fallback_id
        self._save_state()

    def get_fallback(self, primary_id: str) -> Optional[str]:
        return self.fallbacks.get(primary_id)

    def sync_with_storage(self, base_path) -> None:
        for model_id, model in list(self.models.items()):
            if model.local_path:
                if not (base_path / model.local_path).exists():
                    model.status = "evicted"
                    self.models[model_id] = model
        self._save_state()

    def _save_state(self) -> None:
        if not self.state_path:
            return
        settings = get_settings()
        if not settings.persist_state:
            return
        data = {
            "models": {k: v.model_dump(mode="json") for k, v in self.models.items()},
            "fallbacks": self.fallbacks,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        models = data.get("models", {})
        self.models = {k: ModelInfo.model_validate(v) for k, v in models.items()}
        self.fallbacks = data.get("fallbacks", {})


_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
        _registry.load_defaults()
    return _registry
