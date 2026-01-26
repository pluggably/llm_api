"""Tests for HuggingFace integration."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from llm_api.integrations.huggingface import HuggingFaceClient


class TestHuggingFaceClient:
    """Test HuggingFace client functionality."""
    
    @pytest.fixture
    def hf_client(self):
        """Create a HuggingFace client with mocked http client."""
        with patch("llm_api.integrations.huggingface.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            client = HuggingFaceClient(token="test-token")
            # Store mock reference for test access (using object.__setattr__ to avoid type errors)
            object.__setattr__(client, "_test_mock_client", mock_client)
            yield client, mock_client
    
    def test_get_model_info_success(self, hf_client: tuple[HuggingFaceClient, Any]):
        """Test getting model info successfully."""
        client, mock_client = hf_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "meta-llama/Llama-2-7b",
            "author": "meta-llama",
            "downloads": 1000000,
            "likes": 5000,
            "tags": ["text-generation", "pytorch"],
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "config": {
                "hidden_size": 4096,
                "num_attention_heads": 32,
                "num_hidden_layers": 32,
            },
        }
        mock_client.get.return_value = mock_response
        
        info = client.get_model_info("meta-llama/Llama-2-7b")
        
        assert info is not None
        assert info["id"] == "meta-llama/Llama-2-7b"
        assert info["author"] == "meta-llama"
    
    def test_get_model_info_not_found(self, hf_client: tuple[HuggingFaceClient, Any]):
        """Test getting info for non-existent model."""
        client, mock_client = hf_client
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        
        info = client.get_model_info("nonexistent/model")
        
        assert info is None
    
    def test_get_model_readme_success(self, hf_client: tuple[HuggingFaceClient, Any]):
        """Test getting model README."""
        client, mock_client = hf_client
        readme_content = "# Model Card\n\nThis is a test model."
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = readme_content
        mock_client.get.return_value = mock_response
        
        readme = client.get_model_readme("meta-llama/Llama-2-7b")
        
        assert readme == readme_content
    
    def test_get_model_readme_not_found(self, hf_client: tuple[HuggingFaceClient, Any]):
        """Test getting README for model without one."""
        client, mock_client = hf_client
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        
        readme = client.get_model_readme("model/without-readme")
        
        assert readme is None
    
    def test_search_models_success(self, hf_client: tuple[HuggingFaceClient, Any]):
        """Test searching for models."""
        client, mock_client = hf_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "model-1", "author": "author1"},
            {"id": "model-2", "author": "author2"},
        ]
        mock_client.get.return_value = mock_response
        
        results = client.search_models("llama", limit=10)
        
        assert len(results) == 2
        assert results[0]["id"] == "model-1"
    
    def test_enrich_model_metadata_function(self, hf_client):
        """Test enriching model information from HuggingFace using the standalone function."""
        # This test uses the module-level function, not a client method
        from llm_api.integrations.huggingface import enrich_model_metadata
        
        with patch("llm_api.integrations.huggingface.HuggingFaceClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get_model_info.return_value = {
                "id": "TheBloke/TinyLlama-GGUF",
                "modelId": "TheBloke/TinyLlama-GGUF",
                "author": "TheBloke",
                "downloads": 50000,
                "likes": 100,
                "tags": ["text-generation", "gguf"],
                "pipeline_tag": "text-generation",
            }
            mock_client.get_model_readme.return_value = "# TinyLlama Model Card"
            mock_client_cls.return_value = mock_client
            
            enriched = enrich_model_metadata("tiny-llama", "TheBloke/TinyLlama-GGUF")
        
            assert enriched is not None
            assert enriched["hf_repo_id"] == "TheBloke/TinyLlama-GGUF"
            assert enriched["downloads"] == 50000
            assert enriched["documentation"] == "# TinyLlama Model Card"
    
    def test_get_model_files(self, hf_client: tuple[HuggingFaceClient, Any]):
        """Test getting model files list."""
        client, mock_client = hf_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"path": "README.md", "size": 1024, "type": "file"},
            {"path": "config.json", "size": 512, "type": "file"},
            {"path": "model.gguf", "size": 7_000_000_000, "type": "file"},
        ]
        mock_client.get.return_value = mock_response
        
        files = client.get_model_files("TheBloke/TinyLlama-GGUF")
        
        assert files is not None
        assert len(files) == 3
        assert files[2]["path"] == "model.gguf"
