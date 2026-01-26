"""Shared fixtures for integration tests."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from llm_api.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings():
    """Clear settings cache before each test."""
    get_settings.cache_clear()
    # Set up test environment with no auth required
    os.environ["LLM_API_API_KEY"] = ""
    os.environ["LLM_API_JWT_SECRET"] = ""
    os.environ["LLM_API_LOCAL_ONLY"] = "true"
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_api_key():
    """Provide a test API key for authenticated requests."""
    return "test-api-key"


@pytest.fixture
def auth_headers(test_api_key):
    """Provide authentication headers for requests."""
    return {"X-Api-Key": test_api_key}
