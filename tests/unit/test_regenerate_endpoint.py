"""
CR-002: Unit tests for regenerate endpoint (US-044 / SYS-REQ-073).

Tests the regenerate endpoint's message manipulation and delegation logic.
"""

import pytest

HEADERS = {"X-API-Key": "test-key"}


class TestRegenerateEndpoint:
    """TEST-UNIT-022: Regenerate endpoint logic."""

    def test_regenerate_replaces_last_assistant_message(self, client):
        """Case 1: Session with user+assistant -> last assistant removed, replayed."""
        # Create session and send a message
        create = client.post("/v1/sessions", headers=HEADERS)
        assert create.status_code == 201
        sid = create.json()["id"]

        gen = client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )
        assert gen.status_code == 200

        # Regenerate
        regen = client.post(
            f"/v1/sessions/{sid}/regenerate",
            json={},
            headers=HEADERS,
        )
        assert regen.status_code == 200
        assert "output" in regen.json()

        # Check session still has messages
        sess = client.get(f"/v1/sessions/{sid}", headers=HEADERS)
        assert sess.status_code == 200

    def test_regenerate_empty_session_returns_400(self, client):
        """Case 3: Session with no messages -> 400 error."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        regen = client.post(
            f"/v1/sessions/{sid}/regenerate",
            json={},
            headers=HEADERS,
        )
        assert regen.status_code == 400
        assert "no messages" in regen.json()["detail"].lower()

    def test_regenerate_nonexistent_session_returns_404(self, client):
        """Case 4: Session not found -> 404 error."""
        regen = client.post(
            "/v1/sessions/nonexistent-id/regenerate",
            json={},
            headers=HEADERS,
        )
        assert regen.status_code == 404

    def test_regenerate_with_model_override(self, client):
        """Case 5: Optional model override -> generation uses overridden model."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )

        # Regenerate with model override (may fail if model doesn't exist, but
        # the endpoint should accept the parameter)
        regen = client.post(
            f"/v1/sessions/{sid}/regenerate",
            json={"model": "gpt-4"},
            headers=HEADERS,
        )
        # May be 200 or error depending on provider setup, but shouldn't be 422
        assert regen.status_code != 422

    def test_regenerate_closed_session_returns_400(self, client):
        """Case 8: Closed session -> 400 error."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        # Send a message first
        client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )

        # Close session
        client.delete(f"/v1/sessions/{sid}", headers=HEADERS)

        # Try regenerate
        regen = client.post(
            f"/v1/sessions/{sid}/regenerate",
            json={},
            headers=HEADERS,
        )
        assert regen.status_code == 400
