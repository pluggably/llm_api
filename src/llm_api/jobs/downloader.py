from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from llm_api.api.schemas import DownloadJobStatus, ModelDownloadRequest
from llm_api.config import get_settings
from llm_api.jobs.store import JobStore
from llm_api.registry.store import ModelRegistry
from llm_api.storage.manager import StorageManager


@dataclass
class DownloadService:
    registry: ModelRegistry
    jobs: JobStore

    def start_download(self, request: ModelDownloadRequest) -> DownloadJobStatus:
        settings = get_settings()
        model = request.model

        if self.registry.get_model(model.id):
            return DownloadJobStatus(
                job_id="existing",
                model_id=model.id,
                status="completed",
                progress_pct=100,
                created_at=datetime.now(timezone.utc),
            )

        model.status = "downloading"
        model.local_path = f"{model.id}.bin"
        self.registry.add_model(model)

        job = self.jobs.create_job(model.id)

        size_bytes = 1024
        manager = StorageManager(model_path=Path(settings.model_path), max_disk_gb=settings.max_disk_gb)
        if not manager.check_can_download(size_bytes):
            failed = self.jobs.update_job(job.job_id, status="failed", progress_pct=0, error="storage limit")
            if failed is None:
                raise RuntimeError("Download job missing during failure update")
            self.registry.update_model_status(model.id, "failed")
            return failed

        file_path = Path(settings.model_path) / model.local_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"0" * size_bytes)

        job = self.jobs.update_job(job.job_id, status="completed", progress_pct=100)
        if job is None:
            raise RuntimeError("Download job missing during completion update")
        self.registry.update_model_status(model.id, "available")
        return job
