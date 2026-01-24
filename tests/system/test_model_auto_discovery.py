"""TEST-SYS-010: Local model auto-discovery
Traceability: SYS-REQ-018
"""


def test_local_model_auto_discovery(client_factory, tmp_path):
    gguf_path = tmp_path / "tiny.Q4_K_M.gguf"
    gguf_path.write_bytes(b"0" * 10)

    client = client_factory()
    response = client.get("/v1/models", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    body = response.json()
    models = {model["id"]: model for model in body["models"]}

    assert "tiny.Q4_K_M" in models
    discovered = models["tiny.Q4_K_M"]
    assert discovered["local_path"] == "tiny.Q4_K_M.gguf"
    assert discovered["size_bytes"] == 10
    assert discovered["status"] == "available"
