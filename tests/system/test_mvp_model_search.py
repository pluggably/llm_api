"""MVP model search system tests.
Traceability: SYS-REQ-063
"""

from types import SimpleNamespace

import httpx


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        return _FakeResponse(
            [
                {
                    "modelId": "meta-llama/Llama-3",
                    "tags": ["text-generation"],
                    "downloads": 100,
                    "lastModified": "2026-01-26T00:00:00Z",
                    "pipeline_tag": "text-generation",
                }
            ]
        )


def test_huggingface_search_endpoint(client, monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    response = client.get(
        "/v1/models/search?source=huggingface&query=llama",
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body["results"][0]["id"] == "meta-llama/Llama-3"
