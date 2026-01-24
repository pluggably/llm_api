"""
TEST-SYS-004: Health and readiness endpoints
Traceability: SYS-REQ-007
"""
from llm_api.registry import get_registry


class TestHealthReadiness:
    """System tests for health and readiness endpoints."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"]

    def test_ready_returns_200_when_ready(self, client):
        registry = get_registry()
        registry.ready = True
        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_returns_503_when_not_ready(self, client):
        registry = get_registry()
        registry.ready = False
        response = client.get("/ready")
        assert response.status_code == 503
