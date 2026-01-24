from llm_api_client.models import GenerateInput, GenerateRequest


def test_generate_request_serializes_session_fields():
    request = GenerateRequest(
        modality="text",
        input=GenerateInput(prompt="hello"),
        session_id="session-123",
        state_tokens={"seed": "42"},
    )
    payload = request.model_dump(mode="json")

    assert payload["session_id"] == "session-123"
    assert payload["state_tokens"] == {"seed": "42"}
    assert payload["input"]["prompt"] == "hello"
