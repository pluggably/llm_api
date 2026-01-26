"""
TEST-UNIT-005: Config loading
Traceability: SYS-REQ-006
"""
import os

import pytest
from pydantic import ValidationError

from llm_api.config import get_settings


class TestConfigLoading:
    """Unit tests for configuration loading."""

    def test_load_from_env_vars(self, monkeypatch):
        monkeypatch.setenv("LLM_API_API_KEY", "env-key")
        monkeypatch.setenv("LLM_API_PORT", "9090")
        monkeypatch.setenv("LLM_API_MODEL_PATH", "/tmp/models")
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.port == 9090
        assert str(settings.model_path) == "/tmp/models"

    def test_load_from_yaml_file(self, tmp_path, monkeypatch):
        config = tmp_path / "config.yaml"
        config.write_text(
            """
server:
  port: 7777
storage:
  model_path: /tmp/models
auth:
  api_key: yaml-key
"""
        )
        monkeypatch.setenv("LLM_API_CONFIG_FILE", str(config))
        monkeypatch.delenv("LLM_API_MODEL_PATH", raising=False)
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.port == 7777
        assert str(settings.model_path) == "/tmp/models"

    def test_env_vars_override_yaml(self, tmp_path, monkeypatch):
        config = tmp_path / "config.yaml"
        config.write_text(
            """
server:
  port: 8000
auth:
  api_key: yaml-key
"""
        )
        monkeypatch.setenv("LLM_API_CONFIG_FILE", str(config))
        monkeypatch.setenv("LLM_API_PORT", "9000")
        monkeypatch.setenv("LLM_API_API_KEY", "env-key")
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.port == 9000

    def test_settings_load_without_api_key(self, monkeypatch, tmp_path):
        """Test that settings can load without api_key since multiple auth methods are supported.
        
        The system supports several authentication methods:
        - Static API key (via X-Api-Key header)
        - JWT Bearer tokens
        - User-scoped API tokens (database)
        - No auth (development mode)
        
        Therefore, api_key is optional and missing it should not raise an error.
        """
        # Clear all possible sources of the API key
        monkeypatch.delenv("LLM_API_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_CONFIG_FILE", raising=False)
        
        # Change to a directory without .env file
        import os
        monkeypatch.chdir(tmp_path)
        
        # Use a non-existent config file path
        monkeypatch.setenv("LLM_API_CONFIG_FILE", str(tmp_path / "nonexistent.yaml"))
        
        # Clear any cached settings
        get_settings.cache_clear()
        
        # Should load successfully without api_key (no auth mode)
        settings = get_settings()
        assert settings.api_key is None

    def test_default_values_applied(self, monkeypatch):
        monkeypatch.setenv("LLM_API_API_KEY", "env-key")
        monkeypatch.delenv("LLM_API_CONFIG_FILE", raising=False)
        monkeypatch.delenv("LLM_API_MODEL_PATH", raising=False)
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.port == 8080
