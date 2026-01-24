"""TEST-INT-001: Provider error mapping to standard errors
Traceability: SYS-REQ-002
"""
from llm_api.adapters import ProviderError, map_provider_error


class TestProviderErrorMapping:
    """Integration tests for provider error mapping."""

    def test_openai_rate_limit_maps_to_429(self, mock_openai_rate_limit):
        error = map_provider_error(ProviderError(mock_openai_rate_limit, "rate limit"))
        assert error.code == "rate_limit"
        assert error.status_code == 429

    def test_openai_auth_error_maps_to_401(self, mock_openai_auth_error):
        error = map_provider_error(ProviderError(mock_openai_auth_error, "auth error"))
        assert error.code == "auth_error"
        assert error.status_code == 401

    def test_anthropic_overloaded_maps_to_503(self, mock_anthropic_overloaded):
        error = map_provider_error(ProviderError(mock_anthropic_overloaded, "overloaded"))
        assert error.code == "service_unavailable"
        assert error.status_code == 503

    def test_local_runner_oom_maps_to_500(self, mock_local_runner_oom):
        error = map_provider_error(ProviderError(mock_local_runner_oom, "oom"))
        assert error.code == "internal_error"
        assert error.status_code == 500

    def test_timeout_maps_to_504(self, mock_provider_timeout):
        error = map_provider_error(ProviderError(mock_provider_timeout, "timeout"))
        assert error.code == "timeout"
        assert error.status_code == 504
