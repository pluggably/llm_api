from __future__ import annotations

from typing import Any

import httpx

from llm_api.adapters.base import Adapter, ProviderError


class XAIAdapter(Adapter):
    name = "xai"

    def __init__(self, model_id: str, api_key: str | None, base_url: str):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ProviderError(401, "Missing xAI API key")

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, Any]] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        self._ensure_key()
        from llm_api.adapters.openai import _build_openai_messages

        url = f"{self.base_url}/chat/completions"
        
        # Extract parameters with defaults
        params = parameters or {}
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 4096)
        
        payload = {
            "model": self.model_id,
            "messages": _build_openai_messages(
                prompt, system_prompt=system_prompt, history=history
            ),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ProviderError(response.status_code, response.text)
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_image(self, prompt: str) -> bytes:
        raise ProviderError(400, "Image generation not supported for xAI adapter")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "3D generation not supported for xAI adapter")
