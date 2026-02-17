from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Iterable, List

from llm_api.registry.store import ModelRegistry


class StorageLimitError(Exception):
    pass


@dataclass
class StorageManager:
    model_path: Path
    max_disk_gb: float

    def get_disk_usage(self) -> int:
        total = 0
        for path in self.model_path.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def check_can_download(self, download_size_bytes: int) -> bool:
        current = self.get_disk_usage()
        max_bytes = int(self.max_disk_gb * 1024 * 1024 * 1024)
        return current + download_size_bytes <= max_bytes

    def enforce_storage_limit(self, registry: ModelRegistry) -> List[str]:
        evicted: List[str] = []
        max_bytes = int(self.max_disk_gb * 1024 * 1024 * 1024)
        current = self.get_disk_usage()
        if current <= max_bytes:
            return evicted

        def model_sort_key(model):
            failed = 0 if model.status == "failed" else 1
            last_used = model.last_used_at.timestamp() if model.last_used_at else 0
            return (failed, last_used)

        models = sorted(registry.list_models(), key=model_sort_key)
        for model in models:
            if current <= max_bytes:
                break
            if model.local_path:
                file_path = self.model_path / model.local_path
                if file_path.exists():
                    if file_path.is_dir():
                        size = sum(p.stat().st_size for p in file_path.rglob("*") if p.is_file())
                        shutil.rmtree(file_path)
                    else:
                        size = file_path.stat().st_size
                        file_path.unlink()
                    current -= size
                    registry.update_model_status(model.id, "evicted")
                    evicted.append(model.id)
        return evicted
