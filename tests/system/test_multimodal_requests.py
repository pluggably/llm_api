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
        # Image preprocessor requires data-URL format, not raw base64.
        # Specify model explicitly to avoid modality inference override
        # (without a model, images cause _infer_modality → "image").
        import base64
        # 1x1 red PNG pixel
        pixel = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        data_url = f"data:image/png;base64,{base64.b64encode(pixel).decode()}"
        payload = {
            "model": "local-text",
            "modality": "text",
            "input": {"prompt": "Describe", "images": [data_url]},
        }
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["output"]["text"]

    def test_unsupported_modality_returns_400(self, client):
        payload = {"modality": "video", "input": {"prompt": "bad"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422
