from __future__ import annotations

import importlib
import io
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from llm_api.adapters.base import ProviderError
from llm_api.config import get_settings


@lru_cache
def _load_llama(model_path: str):
    try:
        llama_cpp = importlib.import_module("llama_cpp")
    except ImportError as exc:
        raise ProviderError(500, "llama-cpp-python is not installed") from exc
    llama_class = getattr(llama_cpp, "Llama")
    return llama_class(model_path=model_path)


@lru_cache
def _load_diffusion(model_id: str):
    try:
        torch = importlib.import_module("torch")
        diffusers = importlib.import_module("diffusers")
    except ImportError as exc:
        raise ProviderError(500, "diffusers/torch are not installed") from exc
    diffusion_pipeline = getattr(diffusers, "DiffusionPipeline")
    pipe = diffusion_pipeline.from_pretrained(model_id)
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
    return pipe


@lru_cache
def _load_shap_e():
    try:
        torch = importlib.import_module("torch")
        shap_e_diffusion_sample = importlib.import_module("shap_e.diffusion.sample")
        shap_e_diffusion_gaussian = importlib.import_module("shap_e.diffusion.gaussian_diffusion")
        shap_e_models_download = importlib.import_module("shap_e.models.download")
    except ImportError as exc:
        raise ProviderError(500, "shap-e is not installed") from exc
    diffusion_from_config = getattr(shap_e_diffusion_gaussian, "diffusion_from_config")
    load_model = getattr(shap_e_models_download, "load_model")
    load_config = getattr(shap_e_models_download, "load_config")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    xm = load_model("text300M", device=device)
    model = load_model("transmitter", device=device)
    diffusion = diffusion_from_config(load_config("diffusion"))
    return xm, model, diffusion, device


def _find_model_file(model_path: Path) -> Optional[Path]:
    """Find the first valid GGUF model file in the model path."""
    if model_path.is_file():
        return model_path
    if model_path.is_dir():
        # Look for GGUF files
        gguf_files = list(model_path.glob("*.gguf"))
        if gguf_files:
            return gguf_files[0]
        # Fall back to any model file
        for ext in [".bin", ".safetensors", ".pt"]:
            files = list(model_path.glob(f"*{ext}"))
            if files:
                return files[0]
    return None


@dataclass
class LocalRunner:
    """Local OSS runtime runner."""

    def generate_text(self, prompt: str, model_path: Optional[Path] = None) -> str:
        settings = get_settings()
        
        # Priority: explicit path > settings path > default
        if model_path and model_path.exists():
            resolved_path = model_path
        elif model_path:
            # Try relative to model_path setting
            resolved_path = settings.model_path / model_path
        elif settings.local_text_model_path:
            resolved_path = settings.local_text_model_path
        else:
            resolved_path = settings.model_path / "llama.gguf"
        
        # Try to find the actual model file
        actual_file = _find_model_file(resolved_path)
        if not actual_file:
            # Try scanning the models directory for any GGUF
            actual_file = _find_model_file(settings.model_path)
        
        if not actual_file or not actual_file.exists():
            raise ProviderError(400, f"Missing local text model at {resolved_path}")
        
        llama = _load_llama(str(actual_file))
        output = llama(prompt, max_tokens=128)
        return output["choices"][0]["text"]

    def generate_image(self, prompt: str) -> bytes:
        settings = get_settings()
        model_id = settings.local_image_model_id
        pipe = _load_diffusion(model_id)
        image = pipe(prompt, num_inference_steps=2, guidance_scale=0.0).images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def generate_3d(self, prompt: str) -> bytes:
        try:
            torch = importlib.import_module("torch")
            shap_e_diffusion_sample = importlib.import_module("shap_e.diffusion.sample")
            shap_e_util_notebooks = importlib.import_module("shap_e.util.notebooks")
        except ImportError as exc:
            raise ProviderError(500, "shap-e is not installed") from exc

        sample_latents = getattr(shap_e_diffusion_sample, "sample_latents")
        decode_latent_mesh = getattr(shap_e_util_notebooks, "decode_latent_mesh")
        xm, model, diffusion, device = _load_shap_e()
        latents = sample_latents(
            batch_size=1,
            model=xm,
            diffusion=diffusion,
            guidance_scale=3.0,
            model_kwargs=dict(texts=[prompt]),
            progress=False,
            clip_denoised=True,
            use_fp16=torch.cuda.is_available(),
            device=device,
        )
        mesh = decode_latent_mesh(model, latents[0]).tri_mesh()
        buffer = io.BytesIO()
        mesh.export(buffer, file_type="stl")
        return buffer.getvalue()
