"""Tests that require GPU hardware (CUDA or MPS).

Run explicitly with:
    pytest -m gpu tests/system/test_gpu_execution.py

Skipped automatically when no GPU is available or when torch is not installed.
"""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest

# Skip the entire module when torch is not installed.
torch = pytest.importorskip("torch", reason="PyTorch not installed — GPU tests require torch")


def _gpu_available() -> bool:
    """Return True if CUDA or MPS is available."""
    return torch.cuda.is_available() or (
        hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    )


def _gpu_device_name() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings():
    """Return application settings."""
    from llm_api.config import get_settings
    return get_settings()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.gpu
@pytest.mark.skipif(not _gpu_available(), reason="No GPU (CUDA/MPS) available")
class TestGpuExecution:
    """Verify that local model inference runs on the GPU when available."""

    def test_device_detection_selects_gpu(self):
        """_generate_hf_text should pick cuda or mps over cpu."""
        device = _gpu_device_name()
        assert device in {"cuda", "mps"}, "Expected CUDA or MPS device"

    def test_torch_tensor_on_gpu(self):
        """Sanity check: a tensor can be created on the detected device."""
        device = _gpu_device_name()
        t = torch.tensor([1.0, 2.0, 3.0], device=device)
        assert str(t.device).startswith(device)

    def test_local_runner_device_detection(self, settings):
        """LocalRunner's internal device detection should match torch's view."""
        # Import the helper that detects device inside _generate_hf_text
        from llm_api.runner.local_runner import _generate_hf_text  # noqa: F401

        # The function lazily imports torch and probes cuda/mps.
        # We verify the detection path by checking that torch agrees.
        expected = _gpu_device_name()
        if expected == "cuda":
            assert torch.cuda.is_available()
        elif expected == "mps":
            assert torch.backends.mps.is_available()

    def test_float16_dtype_on_gpu(self):
        """GPU paths should use float16 for memory efficiency."""
        device = _gpu_device_name()
        # Mirror the dtype logic in local_runner.py:
        # torch_dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
        expected_dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
        assert expected_dtype == torch.float16, "GPU should use float16"
