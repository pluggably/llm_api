"""
TEST-SYS-005: Observability metrics endpoint
Traceability: SYS-REQ-008
"""
class TestMetricsEndpoint:
    """System tests for observability metrics endpoint."""

    def _parse_metric(self, text: str, metric_name: str) -> float:
        for line in text.splitlines():
            if line.startswith(metric_name + " "):
                return float(line.split(" ", 1)[1])
        return 0.0

    def test_metrics_endpoint_returns_prometheus_format(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        assert "# HELP" in response.text

    def test_request_count_metric_increments(self, client):
        before = client.get("/metrics")
        before_count = self._parse_metric(before.text, "llm_api_request_count")
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        after = client.get("/metrics")
        after_count = self._parse_metric(after.text, "llm_api_request_count")
        assert after_count > before_count

    def test_error_count_metric_increments_on_error(self, client):
        before = client.get("/metrics")
        before_count = self._parse_metric(before.text, "llm_api_error_count")
        response = client.post("/v1/generate", json={"modality": "text"}, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422
        after = client.get("/metrics")
        after_count = self._parse_metric(after.text, "llm_api_error_count")
        assert after_count > before_count

    def test_latency_histogram_recorded(self, client):
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        response = client.get("/metrics")
        assert "llm_api_latency_ms_count" in response.text
