import os

import httpx
import pytest

from llm_api_client import GenerateInput, GenerateRequest, PluggablyClient


def _get_base_url() -> str:
    return os.getenv("LLM_API_BASE_URL", "http://127.0.0.1:8080")


def _get_api_key() -> str:
    # Read from env var first; fall back to parsing .env file which the server loads
    key = os.getenv("LLM_API_API_KEY")
    if key:
        return key
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("LLM_API_API_KEY=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip()
    return "test-key"


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

    # List models first so we can pick a real one for generation
    models = client.list_models()
    assert models.models
    # Pick the first available text model, or fall back to "local-text"
    text_model = next(
        (m.id for m in models.models if getattr(m, "modality", "text") == "text"),
        "local-text",
    )

    response = client.generate_with_session(
        session.id,
        GenerateRequest(
            model=text_model,
            modality="text",
            input=GenerateInput(prompt="Hello"),
        ),
    )
    assert response.session_id == session.id

    providers = client.list_providers()
    assert providers.providers

    closed = client.close_session(session.id)
    assert closed.status == "closed"


def test_llama_31_8b_stream_responds_and_terminates(client):
    base_url = _get_base_url().rstrip("/")
    api_key = _get_api_key()

    models = client.list_models().models
    llama_ids = {
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "local-text",
    }
    available_ids = {m.id for m in models}
    target_model = next((model_id for model_id in llama_ids if model_id in available_ids), None)
    if target_model is None:
        pytest.skip("Llama 3.1 8B model not available in /v1/models")

    payload = {
        "model": target_model,
        "modality": "text",
        "input": {"prompt": "Reply with exactly: pong"},
        "stream": True,
    }

    timeout = httpx.Timeout(connect=10.0, read=240.0, write=30.0, pool=30.0)
    saw_data = False
    saw_done = False
    with httpx.stream(
        "POST",
        f"{base_url}/v1/generate",
        headers={"X-API-Key": api_key},
        json=payload,
        timeout=timeout,
    ) as response:
        assert response.status_code == 200, response.text
        for line in response.iter_lines():
            if not line:
                continue
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                saw_done = True
                break
            saw_data = True

    assert saw_data, "Expected at least one SSE data event from Llama 3.1 stream"
    assert saw_done, "Expected Llama 3.1 SSE stream to terminate with [DONE]"
