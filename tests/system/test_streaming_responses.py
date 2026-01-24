"""
TEST-SYS-007: Streaming text response
Traceability: SYS-REQ-017
"""
class TestStreamingResponses:
    """System tests for streaming text generation responses."""

    def test_stream_flag_returns_sse(self, client):
        payload = {"modality": "text", "input": {"prompt": "Hello"}, "stream": True}
        with client.stream("POST", "/v1/generate", json=payload, headers={"X-API-Key": "test-key"}) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_tokens_arrive_incrementally(self, client):
        payload = {"modality": "text", "input": {"prompt": "Hello world"}, "stream": True}
        with client.stream("POST", "/v1/generate", json=payload, headers={"X-API-Key": "test-key"}) as response:
            events = [line for line in response.iter_lines() if line]
            assert any("data:" in line for line in events)

    def test_stream_error_during_generation(self, client):
        payload = {"modality": "text", "input": {"prompt": "RAISE_ERROR"}, "stream": True}
        with client.stream("POST", "/v1/generate", json=payload, headers={"X-API-Key": "test-key"}) as response:
            events = [line for line in response.iter_lines() if line]
            assert any("error" in line for line in events)

    def test_stream_not_supported_for_image(self, client):
        payload = {"modality": "image", "input": {"prompt": "A cat"}, "stream": True}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 400
