import httpx

from llm_api_client.client import PluggablyClient
from llm_api_client.models import GenerateInput, GenerateRequest


def test_session_helper_calls_generate_endpoint():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={
            "request_id": "req-1",
            "model": "local-text",
            "modality": "text",
            "session_id": "session-123",
            "output": {"text": "ok"},
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    transport = httpx.MockTransport(handler)
    client = PluggablyClient("http://localhost:8080", "test-key", client=httpx.Client(transport=transport))

    session = client.session("session-123")
    response = session.generate(
        GenerateRequest(modality="text", input=GenerateInput(prompt="hi"))
    )

    assert response.session_id == "session-123"
    assert requests[0].url.path == "/v1/sessions/session-123/generate"
