"""
CR-002: System tests for end-to-end API-first refactor changes.

TEST-SYS-020: Image preprocessing E2E
TEST-SYS-021: Session auto-naming E2E
TEST-SYS-022: Regenerate endpoint E2E
"""

import base64
import io
import pytest


HEADERS = {"X-API-Key": "test-key"}


def _make_test_image_data_url(width: int, height: int) -> str:
    """Create a data-URL for a test image of specified dimensions."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


class TestSessionAutoNamingE2E:
    """TEST-SYS-021: End-to-end session auto-naming."""

    def test_auto_name_on_first_message(self, client):
        """Create session -> send message -> session gets auto-title."""
        create = client.post("/v1/sessions", headers=HEADERS)
        assert create.status_code == 201
        sid = create.json()["id"]
        assert create.json().get("title") is None

        # Send first message
        client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Explain gravity"}},
            headers=HEADERS,
        )

        # Session should now have a title
        sess = client.get(f"/v1/sessions/{sid}", headers=HEADERS)
        assert sess.status_code == 200
        assert sess.json()["title"] == "Explain gravity"

    def test_manual_title_preserved(self, client):
        """Set title manually -> send message -> title not overwritten."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        # Set title
        client.put(
            f"/v1/sessions/{sid}",
            json={"title": "My Title"},
            headers=HEADERS,
        )

        # Send message
        client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )

        # Title should be preserved
        sess = client.get(f"/v1/sessions/{sid}", headers=HEADERS)
        assert sess.json()["title"] == "My Title"


class TestRegenerateE2E:
    """TEST-SYS-022: End-to-end regenerate endpoint."""

    def test_regenerate_replaces_response(self, client):
        """Send message -> regenerate -> response generated again."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        # Send initial message
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

    def test_regenerate_empty_session_400(self, client):
        """Regenerate on empty session -> 400."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        regen = client.post(
            f"/v1/sessions/{sid}/regenerate",
            json={},
            headers=HEADERS,
        )
        assert regen.status_code == 400


class TestSessionMessageCountE2E:
    """TEST-SYS-023: End-to-end message count."""

    def test_message_count_increments(self, client):
        """Create session -> send messages -> message_count grows."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        # Initially 0
        sess = client.get(f"/v1/sessions/{sid}", headers=HEADERS)
        assert sess.json()["message_count"] == 0

        # After first message
        client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )
        sess = client.get(f"/v1/sessions/{sid}", headers=HEADERS)
        assert sess.json()["message_count"] == 1

    def test_list_sessions_includes_count(self, client):
        """List sessions -> each includes message_count."""
        create = client.post("/v1/sessions", headers=HEADERS)
        sid = create.json()["id"]

        client.post(
            f"/v1/sessions/{sid}/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )

        listing = client.get("/v1/sessions", headers=HEADERS)
        assert listing.status_code == 200
        sessions = listing.json()["sessions"]
        match = [s for s in sessions if s["id"] == sid]
        assert len(match) == 1
        assert match[0]["message_count"] == 1
