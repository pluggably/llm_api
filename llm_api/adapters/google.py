from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from llm_api.adapters.base import Adapter, ProviderError


class GoogleAdapter(Adapter):
    name = "google"

    def __init__(self, model_id: str, api_key: str | None):
        self.model_id = model_id
        self.api_key = api_key

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ProviderError(401, "Missing Google API key")

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._ensure_key()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent"
        params = {"key": self.api_key}
        contents: list[dict[str, Any]] = []
        if history:
            for turn in history:
                role = "model" if turn["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": str(turn["content"])}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        # Extract parameters with defaults
        req_params = parameters or {}
        temperature = req_params.get("temperature", 0.7)
        max_tokens = req_params.get("max_tokens", 4096)
        
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
        with httpx.Client(timeout=30) as client:
            response = client.post(url, params=params, json=payload)
        if response.status_code >= 400:
            raise ProviderError(response.status_code, response.text)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def generate_image(self, prompt: str) -> bytes:
        raise ProviderError(400, "Image generation not supported for Google adapter")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "3D generation not supported for Google adapter")
