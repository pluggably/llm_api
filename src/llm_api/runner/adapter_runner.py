from __future__ import annotations

from dataclasses import dataclass

from llm_api.adapters import Adapter, ProviderError, StandardError, map_provider_error
from llm_api.runner.local_runner import LocalRunner


@dataclass
class AdapterRunner:
    adapter: Adapter

    def generate_text(self, prompt: str) -> str:
        try:
            return self.adapter.generate(prompt)
        except ProviderError as exc:
            error = map_provider_error(exc)
            raise StandardError(error.code, error.status_code, error.message) from exc

    def generate_image(self, prompt: str) -> bytes:
        if isinstance(self.adapter, LocalRunner):
            return self.adapter.generate_image(prompt)
        return b"EXTERNAL_IMAGE_BYTES"

    def generate_3d(self, prompt: str) -> bytes:
        if isinstance(self.adapter, LocalRunner):
            return self.adapter.generate_3d(prompt)
        return b"EXTERNAL_3D_BYTES"
