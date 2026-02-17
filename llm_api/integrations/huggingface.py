"""HuggingFace integration for model documentation enrichment."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from llm_api.config import get_settings


logger = logging.getLogger(__name__)


class HuggingFaceClient:
    """Client for HuggingFace Hub API."""
    
    BASE_URL = "https://huggingface.co/api"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or get_settings().hf_token
        self._client = httpx.Client(timeout=30.0)
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model information from HuggingFace Hub.
        
        Args:
            model_id: The model ID (e.g., 'TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF')
        
        Returns:
            Model info dict or None if not found
        """
        try:
            url = f"{self.BASE_URL}/models/{model_id}"
            response = self._client.get(url, headers=self._headers())
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch HF model info for {model_id}: {e}")
            return None
    
    def get_model_readme(self, model_id: str) -> Optional[str]:
        """
        Get the README/model card content.
        
        Args:
            model_id: The model ID
        
        Returns:
            README content as string or None
        """
        try:
            url = f"https://huggingface.co/{model_id}/raw/main/README.md"
            response = self._client.get(url, headers=self._headers())
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch HF README for {model_id}: {e}")
            return None
    
    def get_model_files(self, model_id: str) -> Optional[list]:
        """
        Get list of files in the model repository.
        
        Args:
            model_id: The model ID
        
        Returns:
            List of file info dicts or None
        """
        try:
            url = f"{self.BASE_URL}/models/{model_id}/tree/main"
            response = self._client.get(url, headers=self._headers())
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch HF files for {model_id}: {e}")
            return None
    
    def list_models(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        task: Optional[str] = None,
        library: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort: str = "downloads",
        direction: str = "desc",
        limit: int = 50,
        full: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List models from HuggingFace Hub with comprehensive filtering.
        
        Args:
            query: Free-text search query
            author: Filter by author/organization (e.g., 'meta-llama', 'stabilityai')
            task: Filter by pipeline task. Common values:
                - 'text-generation': LLMs for text generation
                - 'text2text-generation': Encoder-decoder models (T5, BART)
                - 'text-classification': Sentiment, NLI, etc.
                - 'image-classification': Image classifiers
                - 'text-to-image': Stable Diffusion, DALL-E style
                - 'image-to-image': Image transformation
                - 'image-to-3d': 3D generation from images
                - 'text-to-3d': 3D generation from text
                - 'automatic-speech-recognition': Speech-to-text
                - 'text-to-speech': TTS
            library: Filter by framework. Common values:
                - 'transformers': Hugging Face Transformers
                - 'diffusers': Stable Diffusion / image generation
                - 'gguf': Quantized models for llama.cpp
                - 'safetensors': Safe tensor format
                - 'pytorch': PyTorch models
                - 'tensorflow': TensorFlow models
            tags: List of tags to filter by (e.g., ['gguf', 'llama'])
            sort: Sort field ('downloads', 'likes', 'created_at', 'modified_at')
            direction: Sort direction ('asc' or 'desc')
            limit: Maximum number of results (1-1000, default 50)
            full: If True, return full model info (slower). If False, return summary.
        
        Returns:
            List of model info dicts with keys:
            - id: Model ID (e.g., 'meta-llama/Llama-2-7b')
            - author: Author/organization
            - downloads: Download count
            - likes: Like count
            - pipeline_tag: Task type
            - tags: List of tags
            - lastModified: Last modification date
        """
        try:
            params: Dict[str, Any] = {
                "limit": min(limit, 1000),
                "sort": sort,
                "direction": direction,
            }
            
            if query:
                params["search"] = query
            if author:
                params["author"] = author
            if task:
                params["pipeline_tag"] = task
            if library:
                params["library"] = library
            if full:
                params["full"] = "true"
            
            # Tags need to be passed as separate filter params
            filter_parts = []
            if tags:
                for tag in tags:
                    filter_parts.append(tag)
            if filter_parts:
                params["filter"] = ",".join(filter_parts)
            
            url = f"{self.BASE_URL}/models"
            response = self._client.get(url, params=params, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to list HF models: {e}")
            return []
    
    def search_models(
        self,
        query: str,
        library: Optional[str] = None,
        task: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for models on HuggingFace Hub.
        
        This is a convenience wrapper around list_models for simple searches.
        
        Args:
            query: Search query
            library: Filter by library (e.g., 'transformers', 'diffusers')
            task: Filter by task (e.g., 'text-generation', 'text-to-image')
            limit: Max results
        
        Returns:
            List of model info dicts
        """
        return self.list_models(
            query=query,
            library=library,
            task=task,
            limit=limit,
        )


def enrich_model_metadata(model_id: str, hf_repo_id: str) -> Dict[str, Any]:
    """
    Enrich model metadata with HuggingFace documentation.
    
    Args:
        model_id: The local model ID
        hf_repo_id: The HuggingFace repository ID
    
    Returns:
        Dict with enriched metadata (description, documentation, parameter guidance)
    """
    client = HuggingFaceClient()
    result = {
        "hf_repo_id": hf_repo_id,
        "description": None,
        "documentation": None,
        "parameter_schema": None,
        "tags": [],
        "downloads": 0,
        "likes": 0,
    }
    
    # Get model info
    info = client.get_model_info(hf_repo_id)
    if info:
        result["description"] = info.get("modelId", "")
        result["tags"] = info.get("tags", [])
        result["downloads"] = info.get("downloads", 0)
        result["likes"] = info.get("likes", 0)
        
        # Extract pipeline tag for task inference
        pipeline_tag = info.get("pipeline_tag")
        if pipeline_tag:
            result["task"] = pipeline_tag
        
        # Extract config for parameter guidance
        config = info.get("config", {})
        if config:
            result["parameter_schema"] = _extract_parameter_schema(config)
    
    # Get README for documentation
    readme = client.get_model_readme(hf_repo_id)
    if readme:
        result["documentation"] = readme
    
    return result


def _extract_parameter_schema(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameter schema from HuggingFace model config."""
    schema = {}
    
    # Common text generation parameters
    if "max_length" in config:
        schema["max_tokens"] = {
            "type": "integer",
            "default": config.get("max_length", 2048),
            "description": "Maximum length of generated text",
        }
    
    if "temperature" in config:
        schema["temperature"] = {
            "type": "float",
            "default": config.get("temperature", 1.0),
            "description": "Sampling temperature",
        }
    
    if "top_p" in config:
        schema["top_p"] = {
            "type": "float",
            "default": config.get("top_p", 1.0),
            "description": "Nucleus sampling probability",
        }
    
    if "top_k" in config:
        schema["top_k"] = {
            "type": "integer",
            "default": config.get("top_k", 50),
            "description": "Top-k sampling",
        }
    
    return schema


# Global instance
_hf_client: Optional[HuggingFaceClient] = None


def get_hf_client() -> HuggingFaceClient:
    """Get the global HuggingFace client instance."""
    global _hf_client
    if _hf_client is None:
        _hf_client = HuggingFaceClient()
    return _hf_client
