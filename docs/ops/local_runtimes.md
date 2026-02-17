# Local Runtime Setup

This project supports local inference for text, image, and 3D. Configure the runtime with env vars from .env.example.

## Text (llama.cpp or HuggingFace)
### GGUF (llama.cpp)
1. Install llama-cpp-python.
2. Download a GGUF model (e.g., a small Mistral or Llama variant).
3. Set `LLM_API_LOCAL_TEXT_MODEL_PATH` to the GGUF file.

### HuggingFace (transformers)
1. Install `transformers` and `torch`.
2. Use a HuggingFace model ID (e.g., `meta-llama/Meta-Llama-3.1-8B-Instruct`).
3. Set `LLM_API_LOCAL_TEXT_MODEL_ID` to that model ID, **or** set `LLM_API_LOCAL_TEXT_MODEL_PATH` to a local model directory containing `config.json`.
4. Optional: set `LLM_API_HF_TRUST_REMOTE_CODE=true` if the model requires custom code.

## Image (diffusers)
1. Install `diffusers` and `torch`.
2. Set `LLM_API_LOCAL_IMAGE_MODEL_ID` to a model like `stabilityai/sdxl-turbo`.

## 3D (Shap-E)
1. Install the `shap-e` package.
2. Set `LLM_API_LOCAL_3D_MODEL_ID` (currently informational; the runtime uses Shap-E defaults).

### Optional: Static 3D preview images
To generate a PNG preview for OBJ outputs, install the optional preview deps:
- `trimesh`, `pyrender`, `Pillow`, `numpy`, `PyOpenGL`, `pyglet`

Notes:
- On headless Linux, `PYOPENGL_PLATFORM=egl` may be required.
- On macOS (no CUDA), previews may still work but are best-effort.

## Recommended baseline models
- **Text**: `meta-llama/Meta-Llama-3.1-8B-Instruct` (HF) or a small GGUF model.
- **Image**: `stabilityai/sdxl-turbo` for fast inference.
- **3D**: Shap-E default text-to-3d model.

## Notes
- These runtimes require large model downloads.
- GPU is optional but strongly recommended for image/3D.
