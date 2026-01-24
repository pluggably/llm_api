"""Session management system tests
Traceability: SYS-REQ-020, SYS-REQ-021, SYS-REQ-022
"""


def test_session_creation_and_reuse(client):
    create = client.post("/v1/sessions", headers={"X-API-Key": "test-key"})
    assert create.status_code == 201
    session_id = create.json()["id"]

    payload = {"modality": "text", "input": {"prompt": "Hello"}}
    first = client.post(f"/v1/sessions/{session_id}/generate", json=payload, headers={"X-API-Key": "test-key"})
    assert first.status_code == 200
    assert first.json().get("session_id") == session_id

    second = client.post(f"/v1/sessions/{session_id}/generate", json=payload, headers={"X-API-Key": "test-key"})
    assert second.status_code == 200
    assert second.json().get("session_id") == session_id


def test_session_lifecycle_reset_and_close(client):
    create = client.post("/v1/sessions", headers={"X-API-Key": "test-key"})
    session_id = create.json()["id"]

    reset = client.post(f"/v1/sessions/{session_id}/reset", headers={"X-API-Key": "test-key"})
    assert reset.status_code == 200

    close = client.delete(f"/v1/sessions/{session_id}", headers={"X-API-Key": "test-key"})
    assert close.status_code == 200
    assert close.json().get("status") == "closed"

    get_closed = client.get(f"/v1/sessions/{session_id}", headers={"X-API-Key": "test-key"})
    assert get_closed.status_code == 200
    assert get_closed.json().get("status") == "closed"


def test_session_state_tokens_passthrough(client):
    create = client.post("/v1/sessions", headers={"X-API-Key": "test-key"})
    session_id = create.json()["id"]

    payload = {
        "modality": "text",
        "input": {"prompt": "Hello"},
        "state_tokens": {"seed": "123"},
    }
    first = client.post(f"/v1/sessions/{session_id}/generate", json=payload, headers={"X-API-Key": "test-key"})
    assert first.status_code == 200
    assert first.json().get("state_tokens") == {"seed": "123"}

    followup = client.post(
        f"/v1/sessions/{session_id}/generate",
        json={"modality": "text", "input": {"prompt": "Next"}},
        headers={"X-API-Key": "test-key"},
    )
    assert followup.status_code == 200
    assert followup.json().get("state_tokens") == {"seed": "123"}
