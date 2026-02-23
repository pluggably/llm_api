from __future__ import annotations

from fastapi.testclient import TestClient

from llm_api.runner.mesh_preview import render_mesh_preview


def test_render_mesh_preview_empty_bytes_returns_none():
    assert render_mesh_preview(b"") is None


def test_generate_3d_includes_preview_artifact(client: TestClient, monkeypatch):
    import llm_api.api.router as router_module

    def _fake_preview(_: bytes) -> bytes:
        return b"PNGDATA"

    monkeypatch.setattr(router_module, "render_mesh_preview", _fake_preview)

    # Use modality-based auto-selection instead of explicit "openai/shap-e" which
    # gets parsed as provider prefix "openai" and fails without an API key.
    response = client.post(
        "/v1/generate",
        json={
            "modality": "3d",
            "input": {"prompt": "a chair"},
        },
        headers={"X-Api-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    artifacts = payload["output"].get("artifacts") or []

    assert any(a["type"] == "image" for a in artifacts)