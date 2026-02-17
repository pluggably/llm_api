from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from llm_api.adapters.base import Adapter, ProviderError

if TYPE_CHECKING:
    from llm_api.runner.local_runner import LocalRunner as LocalRunnerType


class LocalAdapter(Adapter):
    """Base local adapter - routes to appropriate modality-specific implementation."""
    name = "local"

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_id: Optional[str] = None,
        modality: str = "text",
        parameters: Optional[Dict[str, Any]] = None,
        simulate_error: ProviderError | None = None,
    ):
        self.model_path = Path(model_path) if model_path else None
        self.model_id = model_id
        self.modality = modality
        self.parameters = parameters or {}
        self.simulate_error = simulate_error
        # Lazy import to avoid circular dependency
        from llm_api.runner.local_runner import LocalRunner
        self.runner: LocalRunnerType = LocalRunner()

    def generate_text(self, prompt: str) -> str:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_text(
            prompt,
            model_path=self.model_path,
            model_id=self.model_id,
        )

    def generate_image(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_image(
            prompt,
            model_path=self.model_path,
            model_id=self.model_id,
            **self.parameters,
        )

    def generate_3d(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_3d(
            prompt,
            model_path=self.model_path,
            model_id=self.model_id,
            **self.parameters,
        )


class LocalTextAdapter(LocalAdapter):
    """Local adapter for text generation using llama.cpp."""
    name = "local-text"

    def generate_image(self, prompt: str) -> bytes:
        raise ProviderError(400, "Text model cannot generate images")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "Text model cannot generate 3D content")


class LocalImageAdapter(LocalAdapter):
    """Local adapter for image generation using diffusers."""
    name = "local-image"

    def generate_text(self, prompt: str) -> str:
        raise ProviderError(400, "Image model cannot generate text")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "Image model cannot generate 3D content")


class Local3DAdapter(LocalAdapter):
    """Local adapter for 3D generation using shap-e."""
    name = "local-3d"

    def generate_text(self, prompt: str) -> str:
        raise ProviderError(400, "3D model cannot generate text")

    def generate_image(self, prompt: str) -> bytes:
        raise ProviderError(400, "3D model cannot generate images")

