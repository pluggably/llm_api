"""
TEST-UNIT-LOCAL-001: Local text runtime selection
Traceability: SYS-REQ-006
"""
from pathlib import Path

import pytest

from llm_api.runner.local_runner import _resolve_text_runtime


def test_resolve_text_runtime_prefers_gguf(tmp_path, mock_settings):
    gguf_file = tmp_path / "model.gguf"
    gguf_file.write_bytes(b"gguf")

    runtime, target = _resolve_text_runtime(gguf_file, None, mock_settings)

    assert runtime == "llama_cpp"
    assert target == str(gguf_file)


def test_resolve_text_runtime_accepts_hf_dir(tmp_path, mock_settings):
    hf_dir = tmp_path / "phi3"
    hf_dir.mkdir()
    (hf_dir / "config.json").write_text("{}")
    (hf_dir / "model-00001-of-00002.safetensors").write_bytes(b"weights")

    runtime, target = _resolve_text_runtime(hf_dir, None, mock_settings)

    assert runtime == "hf"
    assert target == str(hf_dir)


def test_resolve_text_runtime_accepts_hf_file_with_config(tmp_path, mock_settings):
    hf_dir = tmp_path / "phi3"
    hf_dir.mkdir()
    (hf_dir / "config.json").write_text("{}")
    hf_file = hf_dir / "model-00001-of-00002.safetensors"
    hf_file.write_bytes(b"weights")

    runtime, target = _resolve_text_runtime(hf_file, None, mock_settings)

    assert runtime == "hf"
    assert target == str(hf_dir)


def test_resolve_text_runtime_uses_model_id_when_no_local_model(tmp_path, mock_settings):
    runtime, target = _resolve_text_runtime(None, "microsoft/phi-3-mini-4k-instruct", mock_settings)

    assert runtime == "hf"
    assert target == "microsoft/phi-3-mini-4k-instruct"


def test_resolve_text_runtime_requires_config_for_hf_files(tmp_path, mock_settings):
    hf_file = tmp_path / "model-00001-of-00002.safetensors"
    hf_file.write_bytes(b"weights")

    with pytest.raises(Exception) as excinfo:
        _resolve_text_runtime(hf_file, None, mock_settings)

    assert "config.json" in str(excinfo.value)
