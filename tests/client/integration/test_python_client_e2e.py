import os

import httpx
import pytest

from llm_api_client import GenerateInput, GenerateRequest, PluggablyClient


def _get_base_url() -> str:
    return os.getenv("LLM_API_BASE_URL", "http://127.0.0.1:8080")


def _get_api_key() -> str:
    return os.getenv("LLM_API_API_KEY", "test-local-key")


def _server_available(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def client():
    base_url = _get_base_url()
    if not _server_available(base_url):
        pytest.skip("Local server not reachable for client E2E tests")
    return PluggablyClient(base_url=base_url, api_key=_get_api_key())


def test_python_client_end_to_end(client):
    session = client.create_session()
    assert session.id

    response = client.generate_with_session(
        session.id,
        GenerateRequest(modality="text", input=GenerateInput(prompt="Hello")),
    )
    assert response.session_id == session.id

    models = client.list_models()
    assert models.models

    providers = client.list_providers()
    assert providers.providers

    closed = client.close_session(session.id)
    assert closed.status == "closed"
