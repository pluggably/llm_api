import json

import httpx

from llm_api_client import GenerateInput, GenerateRequest, PluggablyClient, RegenerateRequest


def test_set_default_model_and_search_models():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/default"):
            return httpx.Response(200, json={
                "id": "local-text",
                "name": "Local Text",
                "version": "latest",
                "modality": "text",
                "is_default": True,
            })
        if request.url.path == "/v1/models/search":
            return httpx.Response(200, json={
                "results": [{"id": "hf:demo", "name": "Demo"}],
                "next_cursor": None,
            })
        return httpx.Response(404, json={"detail": "not found"})

    transport = httpx.MockTransport(handler)
    client = PluggablyClient("http://localhost:8080", "test-key", client=httpx.Client(transport=transport))

    model = client.set_default_model("local-text")
    assert model.is_default is True

    results = client.search_models("demo")
    assert results.results[0].id == "hf:demo"

    assert requests[0].method == "POST"
    assert requests[0].url.path == "/v1/models/local-text/default"
    assert requests[1].url.path == "/v1/models/search"
    assert requests[1].url.params["query"] == "demo"


def test_streaming_generate_events():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = "\n".join(
            [
                "data: " + json.dumps({"event": "model_selected", "model": "m1", "model_name": "Model 1"}),
                "",
                "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}}]}),
                "",
                "data: " + json.dumps({
                    "request_id": "req-1",
                    "model": "m1",
                    "modality": "text",
                    "session_id": None,
                    "output": {"text": "Hello"},
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }),
                "",
                "data: [DONE]",
                "",
            ]
        )
        return httpx.Response(200, content=payload)

    transport = httpx.MockTransport(handler)
    client = PluggablyClient("http://localhost:8080", "test-key", client=httpx.Client(transport=transport))

    request = GenerateRequest(modality="text", input=GenerateInput(prompt="hi"), stream=True)
    events = list(client.generate_stream_events(request))

    assert events[0]["type"] == "model_selected"
    assert events[1]["type"] == "text"
    assert events[2]["type"] == "complete"


def test_regenerate_endpoint():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={
            "request_id": "req-1",
            "model": "m1",
            "modality": "text",
            "session_id": "session-123",
            "output": {"text": "ok"},
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    transport = httpx.MockTransport(handler)
    client = PluggablyClient("http://localhost:8080", "test-key", client=httpx.Client(transport=transport))

    response = client.regenerate("session-123", RegenerateRequest())
    assert response.session_id == "session-123"
    assert requests[0].url.path == "/v1/sessions/session-123/regenerate"


def test_get_version():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/version"
        return httpx.Response(
            200,
            json={"version": "sha-xyz987"},
        )

    transport = httpx.MockTransport(handler)
    client = PluggablyClient(
        "http://localhost:8080",
        "test-key",
        client=httpx.Client(transport=transport),
    )

    version = client.get_version()
    assert version.version == "sha-xyz987"
