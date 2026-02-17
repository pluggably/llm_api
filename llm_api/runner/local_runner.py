from __future__ import annotations

import importlib
import io
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Tuple

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


@lru_cache(maxsize=2)
def _load_hf_text_model(
    model_id_or_path: str,
    local_files_only: bool,
    hf_token: Optional[str],
    device: str,
    trust_remote_code: bool,
):
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
    except ImportError as exc:
        raise ProviderError(500, "transformers/torch are not installed") from exc

    AutoTokenizer = getattr(transformers, "AutoTokenizer")
    AutoModelForCausalLM = getattr(transformers, "AutoModelForCausalLM")

    tokenizer = AutoTokenizer.from_pretrained(
        model_id_or_path,
        token=hf_token,
        local_files_only=local_files_only,
        trust_remote_code=trust_remote_code,
    )

    torch_dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id_or_path,
        token=hf_token,
        local_files_only=local_files_only,
        torch_dtype=torch_dtype,
        trust_remote_code=trust_remote_code,
    )

    if device != "cpu":
        model = model.to(device)

    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer, model


def _generate_hf_text(prompt: str, model_id_or_path: str, settings: Any) -> str:
    try:
        torch = importlib.import_module("torch")
    except ImportError as exc:
        raise ProviderError(500, "torch is not installed") from exc

    if Path(model_id_or_path).exists():
        local_files_only = True
        target = str(Path(model_id_or_path))
    else:
        local_files_only = False
        target = model_id_or_path

    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    tokenizer, model = _load_hf_text_model(
        target,
        local_files_only,
        settings.hf_token,
        device,
        settings.hf_trust_remote_code,
    )

    if hasattr(tokenizer, "apply_chat_template"):
        prompt_text = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        prompt_text = prompt

    inputs = tokenizer(prompt_text, return_tensors="pt")
    inputs = inputs.to(device)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=128,
    )

    new_tokens = output_ids[0][inputs.input_ids.shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


@lru_cache(maxsize=8)
def _load_diffusion(model_id: str, local_path: Optional[str] = None):
    """Load a diffusion model from HuggingFace or local path."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Loading diffusion model: {model_id} (local_path={local_path})")
    
    try:
        torch = importlib.import_module("torch")
        diffusers = importlib.import_module("diffusers")
    except ImportError as exc:
        raise ProviderError(500, "diffusers/torch are not installed") from exc
    
    diffusion_pipeline = getattr(diffusers, "DiffusionPipeline")
    
    # If we have a local safetensors file, load from that
    if local_path:
        settings = get_settings()
        full_path = settings.model_path / local_path
        if full_path.exists() and full_path.suffix == ".safetensors":
            # For single safetensors files, we need to load via from_single_file
            StableDiffusionXLPipeline = getattr(diffusers, "StableDiffusionXLPipeline", None)
            if StableDiffusionXLPipeline:
                pipe = StableDiffusionXLPipeline.from_single_file(
                    str(full_path),
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                )
            else:
                pipe = diffusion_pipeline.from_single_file(str(full_path))
        else:
            # Fall back to HuggingFace download
            pipe = diffusion_pipeline.from_pretrained(model_id)
    else:
        pipe = diffusion_pipeline.from_pretrained(model_id)
    
    # Move to appropriate device
    if torch.backends.mps.is_available():
        pipe = pipe.to("mps")
    elif torch.cuda.is_available():
        pipe = pipe.to("cuda")
    
    return pipe


def _get_scheduler_class(name: str):
    """Get a scheduler class by name."""
    try:
        diffusers = importlib.import_module("diffusers")
    except ImportError:
        return None
    
    scheduler_map = {
        "euler": "EulerDiscreteScheduler",
        "euler_a": "EulerAncestralDiscreteScheduler",
        "ddim": "DDIMScheduler",
        "dpm": "DPMSolverMultistepScheduler",
        "dpm++": "DPMSolverMultistepScheduler",
        "lms": "LMSDiscreteScheduler",
        "pndm": "PNDMScheduler",
        "heun": "HeunDiscreteScheduler",
        "unipc": "UniPCMultistepScheduler",
    }
    
    class_name = scheduler_map.get(name.lower())
    if class_name:
        return getattr(diffusers, class_name, None)
    return None


@lru_cache
def _load_shap_e():
    try:
        torch = importlib.import_module("torch")
        shap_e_diffusion_sample = importlib.import_module("shap_e.diffusion.sample")
        shap_e_diffusion_gaussian = importlib.import_module("shap_e.diffusion.gaussian_diffusion")
        shap_e_models_download = importlib.import_module("shap_e.models.download")
    except Exception as exc:
        raise ProviderError(500, f"shap-e import failed: {exc}") from exc
    diffusion_from_config = getattr(shap_e_diffusion_gaussian, "diffusion_from_config")
    load_model = getattr(shap_e_models_download, "load_model")
    load_config = getattr(shap_e_models_download, "load_config")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    xm = load_model("text300M", device=device)
    model = load_model("transmitter", device=device)
    diffusion = diffusion_from_config(load_config("diffusion"))
    return xm, model, diffusion, device


def _find_model_file(model_path: Path, allowed_exts: Optional[list[str]] = None) -> Optional[Path]:
    """Find the first valid model file in the model path."""
    allowed_exts = allowed_exts or [".gguf", ".bin", ".safetensors", ".pt"]
    if model_path.is_file():
        return model_path if model_path.suffix in allowed_exts else None
    if model_path.is_dir():
        for ext in allowed_exts:
            files = list(model_path.glob(f"*{ext}"))
            if files:
                return files[0]
    return None


def _find_text_model_file(model_path: Path) -> Optional[Path]:
    """Find a GGUF model file suitable for llama-cpp text inference."""
    return _find_model_file(model_path, allowed_exts=[".gguf"])


def _find_hf_model_dir(model_path: Path) -> Optional[Path]:
    """Find a HuggingFace model directory (requires config.json)."""
    if not model_path.exists():
        return None
    if model_path.is_dir():
        return model_path if (model_path / "config.json").exists() else None
    if model_path.suffix in {".safetensors", ".bin", ".pt"}:
        candidate = model_path.parent
        return candidate if (candidate / "config.json").exists() else None
    return None


def _resolve_text_runtime(
    model_path: Optional[Path],
    model_id: Optional[str],
    settings: Any,
) -> Tuple[str, str]:
    """Resolve the text runtime and target (gguf path or HF model id/path)."""
    candidate_path: Optional[Path]
    if model_path:
        candidate_path = model_path if model_path.exists() else settings.model_path / model_path
    elif settings.local_text_model_path:
        candidate_path = settings.local_text_model_path
    else:
        candidate_path = settings.model_path / "llama.gguf"

    if candidate_path and candidate_path.exists():
        gguf_file = _find_text_model_file(candidate_path)
        if gguf_file:
            return "llama_cpp", str(gguf_file)

        hf_dir = _find_hf_model_dir(candidate_path)
        if hf_dir:
            return "hf", str(hf_dir)

        if candidate_path.is_file() and candidate_path.suffix in {".safetensors", ".bin", ".pt"}:
            raise ProviderError(
                400,
                "HuggingFace model files require a directory with config.json. "
                "Provide a model directory or a HuggingFace model ID.",
            )

    if model_id or settings.local_text_model_id:
        return "hf", model_id or settings.local_text_model_id

    gguf_fallback = _find_text_model_file(settings.model_path)
    if gguf_fallback:
        return "llama_cpp", str(gguf_fallback)

    hf_fallback = _find_hf_model_dir(settings.model_path)
    if hf_fallback:
        return "hf", str(hf_fallback)

    raise ProviderError(
        400,
        "Missing local text model. Provide a GGUF file or a HuggingFace model ID.",
    )


# Default parameters for different model types
# Use low defaults for CPU - turbo models only need 1-4 steps
DEFAULT_IMAGE_PARAMS = {
    "num_inference_steps": 4,  # sd-turbo only needs 1-4 steps
    "guidance_scale": 0.0,  # sd-turbo works best with guidance_scale=0
    "width": 512,  # Smaller for faster CPU inference
    "height": 512,
}

# Full SDXL models need more steps but still keep reasonable for CPU
SDXL_IMAGE_PARAMS = {
    "num_inference_steps": 20,  # Reasonable balance for CPU
    "guidance_scale": 7.5,
    "width": 1024,
    "height": 1024,
}

DEFAULT_3D_PARAMS = {
    "guidance_scale": 3.0,
    "batch_size": 1,
    "use_karras": True,
    "karras_steps": 32,
    "sigma_min": 1e-3,
    "sigma_max": 160.0,
    "s_churn": 0.0,
}


@dataclass
class LocalRunner:
    """Local OSS runtime runner."""

    def generate_text(
        self,
        prompt: str,
        model_path: Optional[Path] = None,
        model_id: Optional[str] = None,
    ) -> str:
        settings = get_settings()

        runtime, target = _resolve_text_runtime(model_path, model_id, settings)
        if runtime == "llama_cpp":
            llama = _load_llama(target)
            output = llama(prompt, max_tokens=128)
            return output["choices"][0]["text"]

        return _generate_hf_text(prompt, target, settings)

    def generate_image(
        self,
        prompt: str,
        model_path: Optional[Path] = None,
        model_id: Optional[str] = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate an image using diffusers.
        
        Args:
            prompt: Text prompt for image generation
            model_path: Path to local model file (e.g., safetensors)
            model_id: HuggingFace model ID (fallback if no local path)
            **kwargs: Generation parameters:
                - num_inference_steps: Number of denoising steps (default: 50)
                - guidance_scale: Classifier-free guidance scale (default: 7.5)
                - width: Image width (default: 1024)
                - height: Image height (default: 1024)
                - negative_prompt: Negative prompt for guidance
                - seed: Random seed for reproducibility (-1 for random)
                - scheduler: Sampling scheduler name
                - clip_skip: CLIP layers to skip
                - num_images: Number of images per prompt
                - strength: Denoising strength for img2img
                - eta: DDIM eta parameter
        """
        settings = get_settings()
        
        # Determine model to use
        local_path_str = str(model_path) if model_path else None
        effective_model_id = model_id or settings.local_image_model_id
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"generate_image called: model_id={effective_model_id}, local_path={local_path_str}")
        logger.info(f"Cache info: {_load_diffusion.cache_info()}")
        
        pipe = _load_diffusion(effective_model_id, local_path_str)
        
        # Use model-aware defaults
        # Turbo models (sd-turbo, sdxl-turbo) need fewer steps
        is_turbo = "turbo" in effective_model_id.lower()
        base_params = DEFAULT_IMAGE_PARAMS if is_turbo else SDXL_IMAGE_PARAMS
        
        # Merge defaults with provided parameters
        params = {**base_params}
        supported_params = [
            "num_inference_steps", "guidance_scale", "width", "height", 
            "negative_prompt", "eta", "clip_skip"
        ]
        for key in supported_params:
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        
        # Handle num_images -> num_images_per_prompt
        if "num_images" in kwargs and kwargs["num_images"] is not None:
            params["num_images_per_prompt"] = kwargs["num_images"]
        
        # Handle seed/generator (-1 means random)
        seed = kwargs.get("seed")
        if seed is not None and seed != -1:
            torch = importlib.import_module("torch")
            generator = torch.Generator()
            generator.manual_seed(seed)
            params["generator"] = generator
        
        # Handle scheduler change if specified
        scheduler_name = kwargs.get("scheduler")
        if scheduler_name and hasattr(pipe, "scheduler"):
            try:
                scheduler_cls = _get_scheduler_class(scheduler_name)
                if scheduler_cls:
                    pipe.scheduler = scheduler_cls.from_config(pipe.scheduler.config)
            except Exception:
                pass  # Keep default scheduler if change fails
        
        result = pipe(prompt, **params)
        # Return first image only (batch support would need API changes)
        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def generate_3d(
        self,
        prompt: str,
        model_path: Optional[Path] = None,
        model_id: Optional[str] = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate a 3D mesh using shap-e.
        
        Args:
            prompt: Text prompt for 3D generation
            model_path: Path to local model (not yet supported for shap-e)
            model_id: Model ID (not yet supported for shap-e)
            **kwargs: Generation parameters:
                - guidance_scale: Classifier-free guidance scale (default: 3.0)
                - batch_size: Number of samples (default: 1)
        """
        try:
            torch = importlib.import_module("torch")
            shap_e_diffusion_sample = importlib.import_module("shap_e.diffusion.sample")
            shap_e_util_notebooks = importlib.import_module("shap_e.util.notebooks")
        except Exception as exc:
            raise ProviderError(500, f"shap-e import failed: {exc}") from exc

        sample_latents = getattr(shap_e_diffusion_sample, "sample_latents")
        decode_latent_mesh = getattr(shap_e_util_notebooks, "decode_latent_mesh")
        xm, model, diffusion, device = _load_shap_e()
        
        # Merge defaults with provided parameters
        params = {**DEFAULT_3D_PARAMS}
        for key in [
            "guidance_scale",
            "batch_size",
            "use_karras",
            "karras_steps",
            "sigma_min",
            "sigma_max",
            "s_churn",
        ]:
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        
        latents = sample_latents(
            batch_size=params["batch_size"],
            model=xm,
            diffusion=diffusion,
            guidance_scale=params["guidance_scale"],
            model_kwargs=dict(texts=[prompt]),
            progress=False,
            clip_denoised=True,
            use_fp16=torch.cuda.is_available(),
            use_karras=params["use_karras"],
            karras_steps=params["karras_steps"],
            sigma_min=params["sigma_min"],
            sigma_max=params["sigma_max"],
            s_churn=params["s_churn"],
            device=device,
        )
        mesh = decode_latent_mesh(model, latents[0])
        tri_mesh = mesh.tri_mesh()
        text_buffer = io.StringIO()
        tri_mesh.write_obj(text_buffer)
        return text_buffer.getvalue().encode("utf-8")
