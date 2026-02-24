from __future__ import annotations


def test_version_endpoint_returns_deploy_metadata(monkeypatch, client_factory):
    monkeypatch.setenv("LLM_API_APP_VERSION", "sha-abc123")

    client = client_factory()
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "sha-abc123"}
