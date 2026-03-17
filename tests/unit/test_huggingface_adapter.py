from llm_api.adapters.huggingface import HuggingFaceAdapter


def test_huggingface_adapter_uses_router_endpoint() -> None:
    adapter = HuggingFaceAdapter(model_id="Qwen/Qwen2.5-3B-Instruct", api_key=None)
    assert (
        adapter._hf_inference_url
        == "https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-3B-Instruct"
    )
    assert adapter._chat_completions_url == "https://router.huggingface.co/v1/chat/completions"
