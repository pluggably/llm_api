from __future__ import annotations

from typing import Any, Dict, List, Optional

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

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        if self.simulate_error:
            raise self.simulate_error
        self._ensure_key()
        url = "https://api.anthropic.com/v1/messages"
        messages: list[dict[str, str]] = []
        if history:
            for turn in history:
                messages.append({"role": turn["role"], "content": str(turn["content"])})
        messages.append({"role": "user", "content": prompt})
        
        # Extract parameters with defaults
        params = parameters or {}
        max_tokens = params.get("max_tokens", 4096)
        temperature = params.get("temperature", 0.7)
        
        payload: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if system_prompt:
            payload["system"] = system_prompt
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
