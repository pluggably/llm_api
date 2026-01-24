from __future__ import annotations

from typing import TYPE_CHECKING

from llm_api.adapters.base import Adapter, ProviderError

if TYPE_CHECKING:
    from llm_api.runner.local_runner import LocalRunner as LocalRunnerType


class LocalAdapter(Adapter):
    name = "local"

    def __init__(self, simulate_error: ProviderError | None = None):
        self.simulate_error = simulate_error
        # Lazy import to avoid circular dependency
        from llm_api.runner.local_runner import LocalRunner
        self.runner: LocalRunnerType = LocalRunner()

    def generate_text(self, prompt: str) -> str:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_text(prompt)

    def generate_image(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_image(prompt)

    def generate_3d(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        return self.runner.generate_3d(prompt)
