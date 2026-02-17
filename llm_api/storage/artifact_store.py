from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Literal, Optional
from uuid import uuid4

from fastapi import HTTPException

from llm_api.api.schemas import Artifact
from llm_api.config import get_settings


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ArtifactStore:
    base_path: Path
    artifacts: Dict[str, Artifact] = field(default_factory=dict)

    def create_artifact(self, content: bytes, artifact_type: Literal["image", "mesh"]) -> Artifact:
        artifact_id = str(uuid4())
        file_path = self.base_path / artifact_id
        file_path.write_bytes(content)

        settings = get_settings()
        expires_at = now() + timedelta(seconds=settings.artifact_expiry_secs)
        url = f"/v1/artifacts/{artifact_id}"
        artifact = Artifact(id=artifact_id, type=artifact_type, url=url, expires_at=expires_at)
        self.artifacts[artifact_id] = artifact
        return artifact

    def get_artifact(self, artifact_id: str) -> Artifact:
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if artifact.expires_at < now():
            raise HTTPException(status_code=410, detail="Artifact expired")
        return artifact

    def get_artifact_content(self, artifact_id: str) -> bytes:
        artifact = self.get_artifact(artifact_id)
        file_path = self.base_path / artifact.id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Artifact content missing")
        return file_path.read_bytes()


_store: Optional[ArtifactStore] = None


def get_artifact_store() -> ArtifactStore:
    global _store
    if _store is None:
        settings = get_settings()
        base_path = Path(settings.model_path) / "artifacts"
        base_path.mkdir(parents=True, exist_ok=True)
        _store = ArtifactStore(base_path=base_path)
    return _store


def encode_inline(content: bytes) -> str:
    return base64.b64encode(content).decode("utf-8")
