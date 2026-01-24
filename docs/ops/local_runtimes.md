# Local Runtime Setup

This project supports local inference for text, image, and 3D. Configure the runtime with env vars from .env.example.

## Text (llama.cpp)
1. Install llama-cpp-python.
2. Download a GGUF model (e.g., a small Mistral or Llama variant).
3. Set `LLM_API_LOCAL_TEXT_MODEL_PATH` to the GGUF file.

## Image (diffusers)
1. Install `diffusers` and `torch`.
2. Set `LLM_API_LOCAL_IMAGE_MODEL_ID` to a model like `stabilityai/sd-turbo`.

## 3D (Shap-E)
1. Install the `shap-e` package.
2. Set `LLM_API_LOCAL_3D_MODEL_ID` (currently informational; the runtime uses Shap-E defaults).

## Recommended baseline models
- **Text**: A small GGUF model (7B) for local testing.
- **Image**: `stabilityai/sd-turbo` for fast inference.
- **3D**: Shap-E default text-to-3d model.

## Notes
- These runtimes require large model downloads.
- GPU is optional but strongly recommended for image/3D.
