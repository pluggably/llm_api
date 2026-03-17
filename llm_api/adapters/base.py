from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProviderError(Exception):
    status_code: int
    message: str
    error_code: Optional[str] = field(default=None)


@dataclass
class StandardError(Exception):
    code: str
    status_code: int
    message: str


class Adapter:
    name: str = "base"

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The user's current message.
            system_prompt: Optional system-level instructions prepended to the
                conversation (e.g. persona, output-format rules).
            history: Optional list of prior conversation turns, each a dict
                with ``role`` (``"user"`` | ``"assistant"``) and ``content``.
            parameters: Optional generation parameters (temperature, max_tokens, etc.).
        """
        raise NotImplementedError

    def generate_image(self, prompt: str) -> bytes:
        raise NotImplementedError

    def generate_3d(self, prompt: str) -> bytes:
        raise NotImplementedError


def map_provider_error(error: ProviderError) -> StandardError:
    if error.status_code == 429:
        if error.error_code == "insufficient_quota":
            return StandardError(code="insufficient_quota", status_code=429, message=error.message)
        return StandardError(code="rate_limit", status_code=429, message=error.message)
    if error.status_code == 401:
        return StandardError(code="auth_error", status_code=401, message=error.message)
    if error.status_code == 503:
        return StandardError(code="service_unavailable", status_code=503, message=error.message)
    if error.status_code == 504:
        return StandardError(code="timeout", status_code=504, message=error.message)
    return StandardError(code="internal_error", status_code=500, message=error.message)
