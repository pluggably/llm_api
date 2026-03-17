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
    def _hf_inference_url(self) -> str:
        return f"https://router.huggingface.co/hf-inference/models/{self.model_id}"

    @property
    def _chat_completions_url(self) -> str:
        return "https://router.huggingface.co/v1/chat/completions"

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

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, Any]] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            for turn in history:
                messages.append({"role": turn["role"], "content": str(turn["content"])})
        messages.append({"role": "user", "content": prompt})

        # Use HF router OpenAI-compatible chat completions endpoint for text.
        req_params = parameters or {}
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
        }
        if "temperature" in req_params:
            payload["temperature"] = req_params["temperature"]
        if "max_tokens" in req_params:
            payload["max_tokens"] = req_params["max_tokens"]

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                self._chat_completions_url,
                json=payload,
                headers=self._headers(),
            )
        self._raise_for_response(response)

        data = response.json()
        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message")
                    if isinstance(message, dict) and message.get("content") is not None:
                        return str(message["content"])
            # Fallback for non-chat text responses.
            if data.get("generated_text") is not None:
                return str(data["generated_text"])
            if data.get("text") is not None:
                return str(data["text"])
        raise ProviderError(500, "Unexpected Hugging Face text response format")

    def generate_image(self, prompt: str) -> bytes:
        payload: Dict[str, Any] = {"inputs": prompt}
        headers = self._headers()
        headers["Accept"] = "image/png"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self._hf_inference_url, json=payload, headers=headers)
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
