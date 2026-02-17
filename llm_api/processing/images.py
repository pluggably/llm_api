"""Model-driven image preprocessing for the generate pipeline.

Images are resized and re-encoded according to the target model's constraints.
The priority order is:
  1. Model-specific constraints (from ModelCapabilities)
  2. Provider-level defaults (PROVIDER_IMAGE_DEFAULTS)
  3. Pass-through unchanged (if no constraints exist)
"""
from __future__ import annotations

import base64
import io
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider-level defaults: applied when the model has no explicit constraints.
# Values sourced from each provider's documentation.
# ---------------------------------------------------------------------------
PROVIDER_IMAGE_DEFAULTS: Dict[str, Dict[str, object]] = {
    "openai": {"max_edge": 2048, "max_pixels": None, "formats": ["image/png", "image/jpeg", "image/gif", "image/webp"]},
    "anthropic": {"max_edge": 1568, "max_pixels": 1_600_000, "formats": ["image/png", "image/jpeg", "image/gif", "image/webp"]},
    "google": {"max_edge": 3072, "max_pixels": None, "formats": ["image/png", "image/jpeg", "image/webp"]},
    "local": {"max_edge": 1024, "max_pixels": None, "formats": ["image/png", "image/jpeg"]},
}


@dataclass
class ImageConstraints:
    """Resolved image constraints for a model + provider combination."""
    max_edge: Optional[int] = None
    max_pixels: Optional[int] = None
    formats: Optional[List[str]] = None


@dataclass
class PreprocessedImage:
    """A single preprocessed image data-URL."""
    data_url: str
    was_resized: bool = False
    original_size: Optional[Tuple[int, int]] = None
    new_size: Optional[Tuple[int, int]] = None


@dataclass
class PreprocessResult:
    """Result of preprocessing a batch of images."""
    images: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_constraints(
    model_max_edge: Optional[int],
    model_max_pixels: Optional[int],
    model_formats: Optional[List[str]],
    provider: Optional[str],
) -> ImageConstraints:
    """Build effective constraints from model overrides + provider defaults."""
    defaults = PROVIDER_IMAGE_DEFAULTS.get(provider or "", {})
    return ImageConstraints(
        max_edge=model_max_edge or defaults.get("max_edge"),  # type: ignore[arg-type]
        max_pixels=model_max_pixels or defaults.get("max_pixels"),  # type: ignore[arg-type]
        formats=model_formats or defaults.get("formats"),  # type: ignore[arg-type]
    )


def preprocess_images(
    images: List[str],
    *,
    model_max_edge: Optional[int] = None,
    model_max_pixels: Optional[int] = None,
    model_formats: Optional[List[str]] = None,
    provider: Optional[str] = None,
) -> PreprocessResult:
    """Preprocess a list of data-URL images according to model constraints.

    Parameters
    ----------
    images:
        List of data-URL strings (``data:<mime>;base64,<payload>``).
    model_max_edge:
        Model-level maximum edge length (from ``ModelCapabilities``).
    model_max_pixels:
        Model-level maximum total pixel count.
    model_formats:
        Model-level list of accepted MIME types.
    provider:
        Provider name (e.g. ``"openai"``); used to look up defaults
        when model constraints are absent.

    Returns
    -------
    PreprocessResult
        ``images`` — updated data-URL list, ``warnings`` — human-readable notes.
    """
    constraints = resolve_constraints(
        model_max_edge, model_max_pixels, model_formats, provider,
    )

    result = PreprocessResult()
    for idx, data_url in enumerate(images):
        try:
            processed = _process_single(data_url, constraints, idx)
            result.images.append(processed.data_url)
            if processed.was_resized:
                result.warnings.append(
                    f"Image {idx + 1} resized from {processed.original_size} "
                    f"to {processed.new_size} to fit model constraints"
                )
        except Exception:
            logger.exception("Failed to preprocess image %d; passing through unchanged", idx)
            result.images.append(data_url)
            result.warnings.append(f"Image {idx + 1} could not be preprocessed; sent unchanged")

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<payload>.+)$", re.DOTALL)


def _parse_data_url(data_url: str) -> Tuple[str, bytes]:
    """Parse a data-URL into (mime, raw_bytes)."""
    m = _DATA_URL_RE.match(data_url)
    if not m:
        raise ValueError("Not a valid data-URL")
    return m.group("mime"), base64.b64decode(m.group("payload"))


def _encode_data_url(img: Image.Image, target_mime: str) -> str:
    """Encode a PIL Image back to a data-URL string."""
    fmt_map = {
        "image/png": "PNG",
        "image/jpeg": "JPEG",
        "image/webp": "WEBP",
        "image/gif": "GIF",
    }
    pil_format = fmt_map.get(target_mime, "PNG")
    buf = io.BytesIO()

    # Ensure compatible mode for JPEG
    save_img = img
    if pil_format == "JPEG" and img.mode in ("RGBA", "P", "LA"):
        save_img = img.convert("RGB")

    save_img.save(buf, format=pil_format)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{target_mime};base64,{b64}"


def _needs_resize(width: int, height: int, constraints: ImageConstraints) -> bool:
    """Check whether the image exceeds any constraint."""
    if constraints.max_edge:
        if max(width, height) > constraints.max_edge:
            return True
    if constraints.max_pixels:
        if width * height > constraints.max_pixels:
            return True
    return False


def _compute_new_size(
    width: int, height: int, constraints: ImageConstraints
) -> Tuple[int, int]:
    """Compute new (w, h) that satisfies all constraints."""
    w, h = float(width), float(height)

    # Enforce max_edge
    if constraints.max_edge:
        max_dim = max(w, h)
        if max_dim > constraints.max_edge:
            scale = constraints.max_edge / max_dim
            w, h = w * scale, h * scale

    # Enforce max_pixels (after edge scaling)
    if constraints.max_pixels:
        pixels = w * h
        if pixels > constraints.max_pixels:
            scale = (constraints.max_pixels / pixels) ** 0.5
            w, h = w * scale, h * scale

    return max(1, round(w)), max(1, round(h))


def _process_single(
    data_url: str, constraints: ImageConstraints, idx: int
) -> PreprocessedImage:
    """Preprocess a single data-URL image."""
    mime, raw = _parse_data_url(data_url)

    # Open image
    img = Image.open(io.BytesIO(raw))
    original_size = img.size  # (width, height)

    # Determine output MIME
    output_mime = mime
    if constraints.formats and mime not in constraints.formats:
        # Fall back to first accepted format
        output_mime = constraints.formats[0]
        logger.info(
            "Image %d format %s not in accepted list; converting to %s",
            idx, mime, output_mime,
        )

    # Check if resize is needed
    if not _needs_resize(img.width, img.height, constraints):
        # No resize needed — only re-encode if format changed
        if output_mime != mime:
            return PreprocessedImage(
                data_url=_encode_data_url(img, output_mime),
                was_resized=False,
                original_size=original_size,
            )
        return PreprocessedImage(data_url=data_url)

    # Resize
    new_w, new_h = _compute_new_size(img.width, img.height, constraints)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return PreprocessedImage(
        data_url=_encode_data_url(resized, output_mime),
        was_resized=True,
        original_size=original_size,
        new_size=(new_w, new_h),
    )
