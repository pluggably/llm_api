"""Unit tests for the Groq adapter and router integration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llm_api.adapters.base import ProviderError
from llm_api.adapters.groq import GroqAdapter


class TestGroqAdapter:
    def test_name(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key="test-key")
        assert adapter.name == "groq"

    def test_default_base_url(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key="test-key")
        assert adapter.base_url == "https://api.groq.com/openai/v1"

    def test_missing_key_raises(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key=None)
        with pytest.raises(ProviderError) as exc_info:
            adapter.generate_text("hello")
        assert exc_info.value.status_code == 401
        assert "Groq" in exc_info.value.message

    def test_image_not_supported(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key="test")
        with pytest.raises(ProviderError) as exc_info:
            adapter.generate_image("draw a cat")
        assert exc_info.value.status_code == 400

    def test_3d_not_supported(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key="test")
        with pytest.raises(ProviderError) as exc_info:
            adapter.generate_3d("make a cube")
        assert exc_info.value.status_code == 400

    def test_generate_text_delegates_to_openai(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key="test-key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from Groq!"}}],
        }

        with patch("llm_api.adapters.openai.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response

            result = adapter.generate_text("hello")

            assert result == "Hello from Groq!"
            call_args = mock_client.post.call_args
            url = call_args[0][0]
            assert "api.groq.com" in url
            payload = call_args[1]["json"]
            assert payload["model"] == "llama-3.1-8b-instant"

    def test_api_error_propagates(self):
        adapter = GroqAdapter(model_id="llama-3.1-8b-instant", api_key="test-key")
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_response.json.return_value = {"error": {"code": "rate_limit"}}

        with patch("llm_api.adapters.openai.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response

            with pytest.raises(ProviderError) as exc_info:
                adapter.generate_text("hello")
            assert exc_info.value.status_code == 429


class TestGroqRouterIntegration:
    """Verify that groq: prefix routes to GroqAdapter via selector."""

    def test_groq_in_commercial_providers(self):
        from llm_api.router.selector import COMMERCIAL_PROVIDERS
        assert "groq" in COMMERCIAL_PROVIDERS

    def test_groq_model_patterns(self):
        from llm_api.router.selector import _infer_provider_from_model
        assert _infer_provider_from_model("llama-3.1-8b-instant") == "groq"
        assert _infer_provider_from_model("mixtral-8x7b-32768") == "groq"

    def test_adapter_for_groq_provider(self):
        from llm_api.config import Settings
        from llm_api.router.selector import _adapter_for_provider

        settings = Settings(api_key="test-key", groq_api_key="gsk-test")
        adapter = _adapter_for_provider("groq", "llama-3.1-8b-instant", settings)
        assert isinstance(adapter, GroqAdapter)
        assert adapter.model_id == "llama-3.1-8b-instant"

    def test_adapter_for_groq_missing_key(self):
        from llm_api.config import Settings
        from llm_api.router.selector import ProviderNotConfiguredError, _adapter_for_provider

        settings = Settings(api_key="test-key", groq_api_key=None)
        with pytest.raises(ProviderNotConfiguredError, match="Groq"):
            _adapter_for_provider("groq", "llama-3.1-8b-instant", settings)
