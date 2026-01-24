from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderError(Exception):
    status_code: int
    message: str


@dataclass
class StandardError(Exception):
    code: str
    status_code: int
    message: str


class Adapter:
    name: str = "base"

    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_image(self, prompt: str) -> bytes:
        raise NotImplementedError

    def generate_3d(self, prompt: str) -> bytes:
        raise NotImplementedError


def map_provider_error(error: ProviderError) -> StandardError:
    if error.status_code == 429:
        return StandardError(code="rate_limit", status_code=429, message=error.message)
    if error.status_code == 401:
        return StandardError(code="auth_error", status_code=401, message=error.message)
    if error.status_code == 503:
        return StandardError(code="service_unavailable", status_code=503, message=error.message)
    if error.status_code == 504:
        return StandardError(code="timeout", status_code=504, message=error.message)
    return StandardError(code="internal_error", status_code=500, message=error.message)
