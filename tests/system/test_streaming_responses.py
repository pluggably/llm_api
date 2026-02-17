"""
TEST-SYS-007: Streaming text response
Traceability: SYS-REQ-017
"""
import json


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

    def test_stream_flag_for_image_returns_sse_with_complete_response(self, client):
        """Stream flag for non-text returns SSE format with single complete response."""
        payload = {"modality": "image", "input": {"prompt": "A cat"}, "stream": True}
        with client.stream("POST", "/v1/generate", json=payload, headers={"X-API-Key": "test-key"}) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            
            # Parse SSE events
            events = [line for line in response.iter_lines() if line.startswith("data: ")]
            # Should have at least one data event with the response
            assert len(events) >= 1
            
            # Parse the first data event (should be the complete response)
            data_line = events[0]
            if data_line.startswith("data: ") and not data_line.endswith("[DONE]"):
                body = json.loads(data_line[6:])
                assert body.get("modality") == "image"
