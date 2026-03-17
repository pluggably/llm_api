"""Groq adapter — OpenAI-compatible API at api.groq.com."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm_api.adapters.base import Adapter, ProviderError
from llm_api.adapters.openai import OpenAIAdapter, _build_openai_messages


class GroqAdapter(Adapter):
    """
    Adapter for Groq's OpenAI-compatible chat completions API.

    Supported models (non-exhaustive):
      - llama-3.1-8b-instant
      - llama-3.3-70b-versatile
      - mixtral-8x7b-32768
    """

    name = "groq"

    def __init__(
        self,
        model_id: str,
        api_key: str | None,
        base_url: str = "https://api.groq.com/openai/v1",
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        # Delegate actual HTTP calls to OpenAIAdapter (same wire format)
        self._delegate = OpenAIAdapter(
            model_id=model_id,
            api_key=api_key,
            base_url=self.base_url,
        )

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ProviderError(401, "Missing Groq API key. Set LLM_API_GROQ_API_KEY environment variable.")

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._ensure_key()
        return self._delegate.generate_text(
            prompt,
            system_prompt=system_prompt,
            history=history,
            parameters=parameters,
        )

    def generate_image(self, prompt: str) -> bytes:
        raise ProviderError(400, "Image generation not supported for Groq adapter")

    def generate_3d(self, prompt: str) -> bytes:
        raise ProviderError(400, "3D generation not supported for Groq adapter")
