from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from llm_api.api.schemas import DownloadJobStatus, ModelDownloadRequest, ModelSource
from llm_api.background_tasks import get_background_task_registry
from llm_api.config import get_settings
from llm_api.jobs.store import JobStore
from llm_api.registry.store import ModelRegistry
from llm_api.storage.manager import StorageManager

logger = logging.getLogger(__name__)


def _get_huggingface_hub():
    """Lazy import huggingface_hub to avoid hard dependency."""
    try:
        import huggingface_hub
        return huggingface_hub
    except ImportError:
        raise RuntimeError(
            "huggingface_hub is required for downloading models. "
            "Install with: pip install huggingface_hub"
        )


@dataclass
class DownloadService:
    registry: ModelRegistry
    jobs: JobStore
    _running_tasks: dict = field(default_factory=dict)

    def start_download(self, request: ModelDownloadRequest) -> DownloadJobStatus:
        """Start a model download job."""
        settings = get_settings()
        model = request.model

        # Check if model already exists
        existing = self.registry.get_model(model.id)
        if existing and existing.status == "available":
            return DownloadJobStatus(
                job_id="existing",
                model_id=model.id,
                status="completed",
                progress_pct=100,
                created_at=datetime.now(timezone.utc),
            )

        # Register model as downloading
        model.status = "downloading"
        self.registry.add_model(model)

        # Create job
        job = self.jobs.create_job(model.id)

        # Determine download source
        source = request.source
        if source.type == "huggingface":
            repo_id = source.id or source.uri
            if not repo_id:
                failed = self.jobs.update_job(
                    job.job_id, status="failed", progress_pct=0,
                    error="Missing repo_id for huggingface download"
                )
                self.registry.update_model_status(model.id, "failed")
                return failed or job

            install_local = True
            if request.options is not None and request.options.install_local is not None:
                install_local = bool(request.options.install_local)

            if not install_local:
                model.provider = "huggingface"
                model.status = "available"
                model.local_path = None
                model.source = ModelSource(type="huggingface", uri=repo_id)
                self.registry.add_model(model)
                completed = self.jobs.update_job(
                    job.job_id,
                    status="completed",
                    progress_pct=100,
                )
                return completed or job

            # Start async download
            get_background_task_registry().create_task(
                self._download_from_huggingface(
                    job_id=job.job_id,
                    model_id=model.id,
                    repo_id=repo_id,
                    revision=request.options.revision if request.options else None,
                ),
                name=f"download-hf:{model.id}",
            )
            return job

        elif source.type == "url":
            url = source.uri
            if not url:
                failed = self.jobs.update_job(
                    job.job_id, status="failed", progress_pct=0,
                    error="Missing URL for download"
                )
                self.registry.update_model_status(model.id, "failed")
                return failed or job

            get_background_task_registry().create_task(
                self._download_from_url(
                    job_id=job.job_id,
                    model_id=model.id,
                    url=url,
                ),
                name=f"download-url:{model.id}",
            )
            return job

        elif source.type == "local":
            # Local file - just register it
            local_path = source.uri
            if local_path:
                model.local_path = local_path
                model.status = "available"
                self.registry.add_model(model)
                return self.jobs.update_job(job.job_id, status="completed", progress_pct=100) or job

        failed = self.jobs.update_job(
            job.job_id, status="failed", progress_pct=0,
            error=f"Unsupported source type: {source.type}"
        )
        self.registry.update_model_status(model.id, "failed")
        return failed or job

    async def _download_from_huggingface(
        self,
        job_id: str,
        model_id: str,
        repo_id: str,
        revision: Optional[str] = None,
    ) -> None:
        """Download a model from Hugging Face Hub."""
        settings = get_settings()
        hf_hub = _get_huggingface_hub()

        try:
            self.jobs.update_job(job_id, status="running", progress_pct=5)

            # Determine what to download
            target_filename = await self._find_gguf_file(repo_id)

            if not target_filename:
                raise ValueError(f"Could not find downloadable model file in {repo_id}")

            logger.info(f"Preparing download for {repo_id}")
            self.jobs.update_job(job_id, status="running", progress_pct=10)

            manager = StorageManager(
                model_path=Path(settings.model_path),
                max_disk_gb=settings.max_disk_gb,
            )

            model = self.registry.get_model(model_id)

            # For GGUF, download the single file
            if target_filename.endswith(".gguf"):
                logger.info(f"Downloading {repo_id}/{target_filename}")
                local_path = hf_hub.hf_hub_download(
                    repo_id=repo_id,
                    filename=target_filename,
                    local_dir=str(settings.model_path),
                    local_dir_use_symlinks=False,
                    revision=revision,
                )

                self.jobs.update_job(job_id, status="running", progress_pct=90)

                local_path_obj = Path(local_path)
                if model:
                    model.local_path = local_path_obj.name
                    model.status = "available"
                    model.source = ModelSource(type="huggingface", uri=repo_id)
                    self.registry.add_model(model)

                self.jobs.update_job(job_id, status="completed", progress_pct=100)
                logger.info(f"Successfully downloaded {model_id} to {local_path}")
                return

            # For non-GGUF text models, download the full snapshot
            if model and model.modality == "text":
                local_dir = Path(settings.model_path) / "hf" / repo_id.replace("/", "__")
                logger.info(f"Snapshot download {repo_id} to {local_dir}")
                hf_hub.snapshot_download(
                    repo_id=repo_id,
                    local_dir=str(local_dir),
                    local_dir_use_symlinks=False,
                    revision=revision,
                    token=settings.hf_token,
                )

                self.jobs.update_job(job_id, status="running", progress_pct=90)

                if model:
                    model.local_path = str(local_dir.relative_to(Path(settings.model_path)))
                    model.status = "available"
                    model.source = ModelSource(type="huggingface", uri=repo_id)
                    self.registry.add_model(model)

                self.jobs.update_job(job_id, status="completed", progress_pct=100)
                logger.info(f"Successfully downloaded {model_id} to {local_dir}")
                return

            # Otherwise download the single file (image/other)
            logger.info(f"Downloading {repo_id}/{target_filename}")
            local_path = hf_hub.hf_hub_download(
                repo_id=repo_id,
                filename=target_filename,
                local_dir=str(settings.model_path),
                local_dir_use_symlinks=False,
                revision=revision,
            )

            self.jobs.update_job(job_id, status="running", progress_pct=90)

            # Update registry with the local path - model metadata is stored in database
            local_path_obj = Path(local_path)
            if model:
                model.local_path = local_path_obj.name  # Store just the filename
                model.status = "available"
                model.source = ModelSource(type="huggingface", uri=repo_id)
                self.registry.add_model(model)

            self.jobs.update_job(job_id, status="completed", progress_pct=100)
            logger.info(f"Successfully downloaded {model_id} to {local_path}")

        except Exception as e:
            logger.error(f"Download failed for {model_id}: {e}")
            self.jobs.update_job(job_id, status="failed", progress_pct=0, error=str(e))
            self.registry.update_model_status(model_id, "failed")

    async def _find_gguf_file(self, repo_id: str) -> Optional[str]:
        """Find a suitable GGUF file in the repo, preferring Q4_K_M quantization."""
        hf_hub = _get_huggingface_hub()

        try:
            api = hf_hub.HfApi()
            files = api.list_repo_files(repo_id)

            # Filter to GGUF files
            gguf_files = [f for f in files if f.endswith('.gguf')]

            if not gguf_files:
                # Maybe it's a single model file repo
                model_files = [f for f in files if f.endswith(('.bin', '.safetensors', '.pt', '.gguf'))]
                return model_files[0] if model_files else None

            # Prefer Q4_K_M, then Q4_K_S, then Q5_K_M, then any Q4, then first available
            preferences = ['Q4_K_M', 'Q4_K_S', 'Q5_K_M', 'Q4_0', 'Q4_1', 'Q8_0']
            for pref in preferences:
                for f in gguf_files:
                    if pref.lower() in f.lower():
                        return f

            # Return smallest GGUF if no preference matched
            return gguf_files[0]

        except Exception as e:
            logger.warning(f"Could not list files in {repo_id}: {e}")
            return None

    async def _download_from_url(
        self,
        job_id: str,
        model_id: str,
        url: str,
    ) -> None:
        """Download a model from a direct URL."""
        settings = get_settings()

        try:
            import httpx

            self.jobs.update_job(job_id, status="running", progress_pct=5)

            # Determine filename from URL
            filename = url.split('/')[-1].split('?')[0]
            if not filename:
                filename = f"{model_id}.bin"

            local_path = Path(settings.model_path) / filename
            local_path.parent.mkdir(parents=True, exist_ok=True)

            self.jobs.update_job(job_id, status="running", progress_pct=10)

            async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()

                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(local_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                pct = min(90, 10 + int(80 * downloaded / total))
                                self.jobs.update_job(job_id, status="running", progress_pct=pct)

            # Update registry
            model = self.registry.get_model(model_id)
            if model:
                model.local_path = str(local_path)
                model.status = "available"
                self.registry.add_model(model)

            self.jobs.update_job(job_id, status="completed", progress_pct=100)
            logger.info(f"Successfully downloaded {model_id} to {local_path}")

        except Exception as e:
            logger.error(f"URL download failed for {model_id}: {e}")
            self.jobs.update_job(job_id, status="failed", progress_pct=0, error=str(e))
            self.registry.update_model_status(model_id, "failed")
