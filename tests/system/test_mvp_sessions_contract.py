"""MVP session contract system tests.
Traceability: SYS-REQ-065, SYS-REQ-066, SYS-REQ-067
"""


def test_sessions_list_contract(client):
    response = client.get("/v1/sessions", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    body = response.json()
    assert "sessions" in body
    sessions = body["sessions"]
    assert isinstance(sessions, list)
    if sessions:
        session = sessions[0]
        assert "id" in session
        assert "created_at" in session


def test_session_naming_and_update(client):
    create = client.post(
        "/v1/sessions",
        json={"title": "First Session"},
        headers={"X-API-Key": "test-key"},
    )
    assert create.status_code == 201
    session_id = create.json()["id"]
    assert create.json().get("title") == "First Session"

    update = client.put(
        f"/v1/sessions/{session_id}",
        json={"title": "Renamed Session"},
        headers={"X-API-Key": "test-key"},
    )
    assert update.status_code == 200
    assert update.json().get("title") == "Renamed Session"

    listing = client.get("/v1/sessions", headers={"X-API-Key": "test-key"})
    listed = [s for s in listing.json()["sessions"] if s["id"] == session_id]
    assert listed
    assert listed[0].get("title") == "Renamed Session"


def test_session_message_timestamps(client):
    create = client.post("/v1/sessions", headers={"X-API-Key": "test-key"})
    session_id = create.json()["id"]

    payload = {"modality": "text", "input": {"prompt": "Hello"}}
    gen = client.post(
        f"/v1/sessions/{session_id}/generate",
        json=payload,
        headers={"X-API-Key": "test-key"},
    )
    assert gen.status_code == 200

    session = client.get(
        f"/v1/sessions/{session_id}",
        headers={"X-API-Key": "test-key"},
    )
    body = session.json()
    assert "messages" in body
    assert body["messages"]
    for message in body["messages"]:
        assert message.get("created_at")
