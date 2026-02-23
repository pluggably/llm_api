from __future__ import annotations

import httpx

from llm_api.adapters.base import Adapter, ProviderError


class AnthropicAdapter(Adapter):
    name = "anthropic"

    def __init__(
        self,
        model_id: str,
        api_key: str | None,
        simulate_error: ProviderError | None = None,
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.simulate_error = simulate_error

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ProviderError(401, "Missing Anthropic API key")

    def generate_text(self, prompt: str) -> str:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model_id,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            error_code: str | None = None
            try:
                error_code = response.json().get("error", {}).get("type")
            except Exception:
                pass
            raise ProviderError(response.status_code, response.text, error_code=error_code)
        data = response.json()
        return data["content"][0]["text"]

    def generate_image(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        raise ProviderError(400, "Image generation not supported for Anthropic adapter")

    def generate_3d(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        raise ProviderError(400, "3D generation not supported for Anthropic adapter")
