"""
CR-002: Unit tests for absolute artifact URLs (US-045 / SYS-REQ-074)
and session message count (US-046 / SYS-REQ-075).
"""

import os
from datetime import datetime, timezone
import pytest

from llm_api.api.router import _absolute_artifact_url, _make_output_urls_absolute
from llm_api.api.schemas import Artifact, GenerateOutput
from llm_api.sessions.store import SessionStore
from llm_api.db import database as db_module
from llm_api.config import get_settings


HEADERS = {"X-API-Key": "test-key"}


class TestAbsoluteArtifactUrls:
    """TEST-UNIT-023: Absolute artifact URL generation."""

    def test_localhost_url(self):
        """Case 1: Relative URL + localhost base -> absolute localhost URL."""
        result = _absolute_artifact_url(
            "http://localhost:8080/", "/v1/artifacts/abc.png"
        )
        assert result == "http://localhost:8080/v1/artifacts/abc.png"

    def test_production_url(self):
        """Case 2: Relative URL + production base -> absolute production URL."""
        result = _absolute_artifact_url(
            "https://api.example.com/", "/v1/artifacts/abc.png"
        )
        assert result == "https://api.example.com/v1/artifacts/abc.png"

    def test_already_absolute_url_unchanged(self):
        """Case 3: Already absolute URL -> returned unchanged."""
        url = "https://cdn.example.com/img.png"
        result = _absolute_artifact_url("http://localhost:8080/", url)
        assert result == url

    def test_make_output_urls_absolute_with_artifacts(self):
        """Case 4: GenerateOutput with artifacts -> all URLs made absolute."""
        exp = datetime.now(timezone.utc)
        output = GenerateOutput(
            text="result",
            artifacts=[
                Artifact(id="a1", type="image", url="/v1/artifacts/img1.png", expires_at=exp),
                Artifact(id="a2", type="image", url="/v1/artifacts/img2.png", expires_at=exp),
            ],
        )
        updated = _make_output_urls_absolute(output, "http://localhost:8080")
        assert all(
            a.url.startswith("http://localhost:8080")
            for a in updated.artifacts
        )

    def test_make_output_urls_absolute_no_artifacts(self):
        """Case 5: GenerateOutput without artifacts -> no error."""
        output = GenerateOutput(text="result")
        updated = _make_output_urls_absolute(output, "http://localhost:8080")
        assert updated.text == "result"


@pytest.fixture
def _fresh_db(tmp_path):
    """Create an isolated DB for each test."""
    os.environ["LLM_API_API_KEY"] = "test-key"
    os.environ["LLM_API_MODEL_PATH"] = str(tmp_path)
    os.environ.setdefault("LLM_API_DEFAULT_MODEL", "local-text")
    get_settings.cache_clear()
    db_module.close_db()
    db_module._engine = None
    db_module._SessionLocal = None
    yield
    db_module.close_db()
    db_module._engine = None
    db_module._SessionLocal = None


class TestSessionMessageCount:
    """TEST-UNIT-024: Session message count."""

    @pytest.fixture(autouse=True)
    def setup(self, _fresh_db):
        pass

    def test_new_session_zero_count(self):
        """Case 1: New session -> message_count is 0."""
        store = SessionStore()
        session = store.create_session()
        assert session.message_count == 0

    def test_session_with_messages(self):
        """Case 2: Session with 2 messages -> message_count is 2."""
        store = SessionStore()
        session = store.create_session()
        store.append_message(
            session.id, "text", {"prompt": "Hi"}, {"text": "Hello"}, None
        )
        store.append_message(
            session.id, "text", {"prompt": "Bye"}, {"text": "Goodbye"}, None
        )
        updated = store.get_session(session.id)
        assert updated.message_count == 2

    def test_count_increments_on_append(self):
        """Case 3: After append -> message_count increments."""
        store = SessionStore()
        session = store.create_session()
        result = store.append_message(
            session.id, "text", {"prompt": "Hi"}, {"text": "Hello"}, None
        )
        assert result.message_count == 1
        result2 = store.append_message(
            session.id, "text", {"prompt": "More"}, {"text": "Sure"}, None
        )
        assert result2.message_count == 2

    def test_count_resets_on_reset(self):
        """Case 4: After reset -> message_count is 0."""
        store = SessionStore()
        session = store.create_session()
        store.append_message(
            session.id, "text", {"prompt": "Hi"}, {"text": "Hello"}, None
        )
        reset = store.reset_session(session.id)
        assert reset is not None
        # Fetch again to confirm
        updated = store.get_session(session.id)
        assert updated.message_count == 0

    def test_list_sessions_includes_count(self):
        """Case 5: List sessions -> each includes message_count."""
        store = SessionStore()
        session = store.create_session()
        store.append_message(
            session.id, "text", {"prompt": "Hi"}, {"text": "Hello"}, None
        )
        summaries = store.list_sessions()
        match = [s for s in summaries if s.id == session.id]
        assert len(match) == 1
        assert match[0].message_count == 1
