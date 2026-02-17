from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from llm_api.api.schemas import DownloadJobStatus
from llm_api.config import get_settings


@dataclass
class JobStore:
    jobs: Dict[str, DownloadJobStatus] = field(default_factory=dict)
    state_path: Optional[Path] = None

    def create_job(self, model_id: str) -> DownloadJobStatus:
        self._ensure_state_path()
        job_id = str(uuid4())
        job = DownloadJobStatus(
            job_id=job_id,
            model_id=model_id,
            status="queued",
            progress_pct=0,
            created_at=datetime.now(timezone.utc),
        )
        self.jobs[job_id] = job
        self._save_state()
        return job

    def update_job(self, job_id: str, **kwargs) -> Optional[DownloadJobStatus]:
        self._ensure_state_path()
        job = self.jobs.get(job_id)
        if not job:
            return None
        updated = job.model_copy(update=kwargs)
        self.jobs[job_id] = updated
        self._save_state()
        return updated

    def cancel_job(self, job_id: str) -> Optional[DownloadJobStatus]:
        return self.update_job(job_id, status="cancelled")

    def get_job(self, job_id: str) -> Optional[DownloadJobStatus]:
        self._ensure_state_path()
        return self.jobs.get(job_id)

    def _ensure_state_path(self) -> None:
        if self.state_path:
            return
        settings = get_settings()
        self.state_path = Path(settings.model_path) / "jobs.json"
        if settings.persist_state:
            self._load_state()

    def _save_state(self) -> None:
        if not self.state_path:
            return
        settings = get_settings()
        if not settings.persist_state:
            return
        data = {k: v.model_dump(mode="json") for k, v in self.jobs.items()}
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.jobs = {k: DownloadJobStatus.model_validate(v) for k, v in data.items()}


_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store
