from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from llm_api.adapters.base import Adapter, ProviderError


def _build_openai_messages(
    prompt: str,
    *,
    system_prompt: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Build an OpenAI-style messages array from prompt + optional context."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        for turn in history:
            messages.append({"role": turn["role"], "content": str(turn["content"])})
    messages.append({"role": "user", "content": prompt})
    return messages


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
            error_code: str | None = None
            try:
                error_code = response.json().get("error", {}).get("code")
            except Exception:
                pass
            raise ProviderError(response.status_code, response.text, error_code=error_code)
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
