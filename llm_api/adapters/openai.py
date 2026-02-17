from __future__ import annotations

import httpx

from llm_api.adapters.base import Adapter, ProviderError


class OpenAIAdapter(Adapter):
    name = "openai"

    def __init__(
        self,
        model_id: str,
        api_key: str | None,
        base_url: str,
        simulate_error: ProviderError | None = None,
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.simulate_error = simulate_error

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ProviderError(401, "Missing OpenAI API key")

    def generate_text(self, prompt: str) -> str:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ProviderError(response.status_code, response.text)
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_image(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        raise ProviderError(400, "Image generation not supported in this adapter")

    def generate_3d(self, prompt: str) -> bytes:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        raise ProviderError(400, "3D generation not supported in this adapter")
