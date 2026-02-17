"""
CR-002: Unit tests for image preprocessing (US-042 / SYS-REQ-071).
"""

import base64
import io
import pytest

from llm_api.processing.images import preprocess_images


def _make_test_image(width: int, height: int, fmt: str = "PNG") -> str:
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode()
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[fmt]
    return f"data:{mime};base64,{b64}"


def _decode_data_url(data_url: str):
    from PIL import Image
    _, payload = data_url.split(",", 1)
    raw = base64.b64decode(payload)
    return Image.open(io.BytesIO(raw))


class TestImagePreprocessing:

    def test_image_within_limits_unchanged(self):
        image = _make_test_image(1024, 768)
        result = preprocess_images([image], model_max_edge=2048)
        assert len(result.images) == 1
        assert len(result.warnings) == 0
        img = _decode_data_url(result.images[0])
        assert img.size == (1024, 768)

    def test_image_exceeding_max_edge_resized(self):
        image = _make_test_image(4096, 2048)
        result = preprocess_images([image], model_max_edge=1024)
        assert len(result.warnings) == 1
        assert "resized" in result.warnings[0].lower()
        img = _decode_data_url(result.images[0])
        assert max(img.size) <= 1024
        assert img.size == (1024, 512)

    def test_image_exceeding_max_pixels_resized(self):
        image = _make_test_image(2000, 2000)
        result = preprocess_images(
            [image], model_max_pixels=1_000_000, model_max_edge=4096
        )
        assert len(result.warnings) == 1
        img = _decode_data_url(result.images[0])
        assert img.size[0] * img.size[1] <= 1_000_000

    def test_no_constraints_no_provider_passthrough(self):
        image = _make_test_image(8000, 6000)
        result = preprocess_images([image])
        assert len(result.warnings) == 0
        img = _decode_data_url(result.images[0])
        assert img.size == (8000, 6000)

    def test_provider_defaults_used(self):
        image = _make_test_image(4096, 4096)
        result = preprocess_images([image], provider="openai")
        assert len(result.warnings) == 1
        img = _decode_data_url(result.images[0])
        assert max(img.size) <= 2048

    def test_mixed_images_selective_resize(self):
        small = _make_test_image(512, 512)
        large = _make_test_image(2048, 2048)
        result = preprocess_images([small, large], model_max_edge=1024)
        assert len(result.warnings) == 1
        r0 = _decode_data_url(result.images[0])
        r1 = _decode_data_url(result.images[1])
        assert r0.size == (512, 512)
        assert max(r1.size) <= 1024

    def test_malformed_data_url_passed_through(self):
        result = preprocess_images(["not-a-data-url"], model_max_edge=1024)
        assert len(result.images) == 1
        assert result.images[0] == "not-a-data-url"
        assert len(result.warnings) == 1
        assert "could not be preprocessed" in result.warnings[0].lower()

    def test_various_input_formats(self):
        for fmt in ["PNG", "JPEG", "WEBP"]:
            image = _make_test_image(1024, 768, fmt=fmt)
            result = preprocess_images([image], model_max_edge=512)
            assert len(result.warnings) == 1
            img = _decode_data_url(result.images[0])
            assert max(img.size) <= 512

    def test_portrait_orientation_aspect_ratio(self):
        image = _make_test_image(1536, 4096)
        result = preprocess_images([image], model_max_edge=1024)
        img = _decode_data_url(result.images[0])
        assert max(img.size) <= 1024
        assert img.size[1] == 1024
        assert img.size[0] < img.size[1]
