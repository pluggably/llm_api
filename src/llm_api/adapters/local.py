from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from llm_api.adapters.base import Adapter, ProviderError

if TYPE_CHECKING:
    from llm_api.runner.local_runner import LocalRunner as LocalRunnerType


class LocalAdapter(Adapter):
    name = "local"

    def __init__(
        self,
        model_path: Optional[str] = None,
        simulate_error: ProviderError | None = None,
    ):
        self.model_path = Path(model_path) if model_path else None
        self.simulate_error = simulate_error
        # Lazy import to avoid circular dependency
        from llm_api.runner.local_runner import LocalRunner
        self.runner: LocalRunnerType = LocalRunner()

    def generate_text(self, prompt: str) -> str:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_text(prompt, model_path=self.model_path)

    def generate_image(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_image(prompt)

    def generate_3d(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_3d(prompt)
