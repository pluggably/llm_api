"""TEST-UNIT-001: Invalid payload validation
Traceability: SYS-REQ-001
"""
class TestValidationInvalidPayload:
    """Unit tests for request payload validation."""

    def test_missing_required_field_returns_422(self, client):
        payload = {"modality": "text"}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422
        assert "input" in response.text

    def test_invalid_modality_returns_422(self, client):
        payload = {"modality": "video", "input": {"prompt": "hi"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422
        assert "text" in response.text

    def test_temperature_out_of_range_returns_422(self, client):
        payload = {
            "modality": "text",
            "input": {"prompt": "hi"},
            "parameters": {"temperature": 5.0},
        }
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422
        assert "temperature" in response.text

    def test_malformed_json_returns_400(self, client):
        response = client.post(
            "/v1/generate",
            content=b"{bad-json",
            headers={"X-API-Key": "test-key", "Content-Type": "application/json"},
        )
        assert response.status_code in {400, 422}
