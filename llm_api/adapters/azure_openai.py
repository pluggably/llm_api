from __future__ import annotations

from typing import Any

import httpx

from llm_api.adapters.base import Adapter, ProviderError


class AzureOpenAIAdapter(Adapter):
    name = "azure"

    def __init__(
        self,
        deployment: str,
        api_key: str | None,
        endpoint: str | None,
        api_version: str,
    ):
        self.deployment = deployment
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/") if endpoint else None
        self.api_version = api_version

    def _ensure_config(self) -> None:
        if not self.api_key or not self.endpoint:
            raise ProviderError(401, "Missing Azure OpenAI API key or endpoint")

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, Any]] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        self._ensure_config()
        assert self.endpoint is not None
        assert self.api_key is not None
        from llm_api.adapters.openai import _build_openai_messages

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
        api_params = {"api-version": self.api_version}
        
        # Extract parameters with defaults
        req_params = parameters or {}
        temperature = req_params.get("temperature", 0.7)
        max_tokens = req_params.get("max_tokens", 4096)
        
        payload = {
            "messages": _build_openai_messages(
                prompt, system_prompt=system_prompt, history=history
            ),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"api-key": self.api_key}
        with httpx.Client(timeout=30) as client:
            response = client.post(url, params=api_params, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ProviderError(response.status_code, response.text)
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_image(self, prompt: str) -> bytes:
        raise ProviderError(400, "Image generation not supported for Azure adapter")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "3D generation not supported for Azure adapter")
