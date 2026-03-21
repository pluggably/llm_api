from llm_api.adapters.huggingface import HuggingFaceAdapter


def test_huggingface_adapter_uses_router_endpoint() -> None:
    adapter = HuggingFaceAdapter(model_id="mistralai/Mistral-7B-Instruct-v0.3", api_key=None)
    assert (
        adapter._hf_inference_url
        == "https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.3"
    )
    assert adapter._chat_completions_url == "https://router.huggingface.co/v1/chat/completions"
