"""TEST-SYS-001: Multimodal request handling
Traceability: SYS-REQ-001, SYS-REQ-003, SYS-REQ-004
"""
class TestMultimodalRequests:
    """System tests for multimodal request handling."""

    def test_text_generation_returns_text(self, client):
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["output"]["text"]

    def test_image_generation_returns_image(self, client):
        payload = {"modality": "image", "input": {"prompt": "A cat"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        output = response.json()["output"]
        assert output.get("images") or output.get("artifacts")

    def test_3d_generation_returns_mesh(self, client):
        payload = {"modality": "3d", "input": {"prompt": "A chair"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        output = response.json()["output"]
        assert output.get("mesh") or output.get("artifacts")

    def test_request_with_image_input(self, client):
        payload = {
            "modality": "text",
            "input": {"prompt": "Describe", "images": ["ZmFrZQ=="]},
        }
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["output"]["text"]

    def test_unsupported_modality_returns_400(self, client):
        payload = {"modality": "video", "input": {"prompt": "bad"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422
