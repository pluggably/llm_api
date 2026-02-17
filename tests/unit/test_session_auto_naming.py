"""
CR-002: Unit tests for session auto-naming (US-043 / SYS-REQ-072).

Tests that the session store auto-generates a title from the first
user message when no title is set.
"""

import os
import pytest
from pathlib import Path

from llm_api.sessions.store import SessionStore
from llm_api.db import database as db_module
from llm_api.config import get_settings


@pytest.fixture(autouse=True)
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


class TestSessionAutoNaming:
    """TEST-UNIT-021: Session auto-naming logic."""

    def test_first_message_sets_title(self):
        """Case 1: First message on untitled session -> title set."""
        store = SessionStore()
        session = store.create_session()
        assert session.title is None
        store.append_message(
            session.id, "text",
            {"prompt": "Tell me about quantum computing"},
            {"text": "Quantum computing is..."},
            None,
        )
        updated = store.get_session(session.id)
        assert updated.title == "Tell me about quantum computing"

    def test_short_prompt_full_title(self):
        """Case 2: Prompt shorter than 50 chars -> title is full prompt."""
        store = SessionStore()
        session = store.create_session()
        store.append_message(
            session.id, "text",
            {"prompt": "Hello"},
            {"text": "Hi!"},
            None,
        )
        updated = store.get_session(session.id)
        assert updated.title == "Hello"

    def test_long_prompt_truncated(self):
        """Case 3: Prompt longer than 50 chars -> truncated with ellipsis."""
        store = SessionStore()
        session = store.create_session()
        long_prompt = "A" * 100
        store.append_message(
            session.id, "text",
            {"prompt": long_prompt},
            {"text": "response"},
            None,
        )
        updated = store.get_session(session.id)
        assert updated.title is not None
        assert len(updated.title) == 50
        assert updated.title.endswith("...")

    def test_existing_title_not_overwritten(self):
        """Case 4: Session with title -> title preserved on message."""
        store = SessionStore()
        session = store.create_session()
        store.update_session(session.id, title="My Custom Title")
        store.append_message(
            session.id, "text",
            {"prompt": "This should not become the title"},
            {"text": "response"},
            None,
        )
        updated = store.get_session(session.id)
        assert updated.title == "My Custom Title"

    def test_second_message_no_rename(self):
        """Case 5: Second message -> title not changed."""
        store = SessionStore()
        session = store.create_session()
        store.append_message(
            session.id, "text",
            {"prompt": "First message"},
            {"text": "response 1"},
            None,
        )
        store.append_message(
            session.id, "text",
            {"prompt": "Second message should not rename"},
            {"text": "response 2"},
            None,
        )
        updated = store.get_session(session.id)
        assert updated.title == "First message"

    def test_empty_prompt_no_title(self):
        """Case 6: Empty prompt -> title remains None."""
        store = SessionStore()
        session = store.create_session()
        store.append_message(
            session.id, "text",
            {"prompt": ""},
            {"text": "response"},
            None,
        )
        updated = store.get_session(session.id)
        assert updated.title is None
