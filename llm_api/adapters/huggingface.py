from __future__ import annotations

import base64
from typing import Any, Dict

import httpx

from llm_api.adapters.base import Adapter, ProviderError


class HuggingFaceAdapter(Adapter):
    """Adapter for Hugging Face hosted inference API."""

    name = "huggingface"

    def __init__(
        self,
        model_id: str,
        api_key: str | None,
        timeout_seconds: float = 120.0,
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def _url(self) -> str:
        return f"https://api-inference.huggingface.co/models/{self.model_id}"

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _raise_for_response(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        message = response.text
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                message = str(payload["error"])
        except Exception:
            pass
        raise ProviderError(response.status_code, message)

    def generate_text(self, prompt: str) -> str:
        payload: Dict[str, Any] = {"inputs": prompt}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self._url, json=payload, headers=self._headers())
        self._raise_for_response(response)

        data = response.json()
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                if "generated_text" in first:
                    return str(first["generated_text"])
                if "summary_text" in first:
                    return str(first["summary_text"])
                if "translation_text" in first:
                    return str(first["translation_text"])
        if isinstance(data, dict):
            if "generated_text" in data:
                return str(data["generated_text"])
            if "text" in data:
                return str(data["text"])
        raise ProviderError(500, "Unexpected Hugging Face text response format")

    def generate_image(self, prompt: str) -> bytes:
        payload: Dict[str, Any] = {"inputs": prompt}
        headers = self._headers()
        headers["Accept"] = "image/png"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self._url, json=payload, headers=headers)
        self._raise_for_response(response)

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("image/"):
            return response.content

        # Some endpoints may return base64 JSON payloads.
        try:
            data = response.json()
            if isinstance(data, dict) and isinstance(data.get("image"), str):
                return base64.b64decode(data["image"])
        except Exception:
            pass
        raise ProviderError(500, "Unexpected Hugging Face image response format")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "3D generation is not supported by Hugging Face hosted adapter")
