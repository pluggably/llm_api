"""TEST-UNIT-004: Storage policy enforcement
Traceability: SYS-REQ-012, SYS-NFR-007
"""
from pathlib import Path

from llm_api.storage.manager import StorageManager
from llm_api.api.schemas import ModelInfo
from llm_api.registry.store import ModelRegistry


class TestStoragePolicy:
    """Unit tests for storage policy enforcement."""

    def test_get_disk_usage_returns_bytes(self, tmp_model_dir):
        file_path = tmp_model_dir / "file.bin"
        file_path.write_bytes(b"x" * 10)
        manager = StorageManager(model_path=tmp_model_dir, max_disk_gb=1)
        assert manager.get_disk_usage() == 10

    def test_under_limit_allows_download(self, tmp_model_dir, mock_settings):
        manager = StorageManager(model_path=tmp_model_dir, max_disk_gb=100)
        assert manager.check_can_download(10 * 1024 * 1024) is True

    def test_over_limit_blocks_download(self, tmp_model_dir, mock_settings):
        big_file = tmp_model_dir / "big.bin"
        big_file.write_bytes(b"x" * 1024)
        manager = StorageManager(model_path=tmp_model_dir, max_disk_gb=0.0000001)
        assert manager.check_can_download(10) is False

    def test_evict_lru_when_over_limit(self, tmp_model_dir, mock_registry):
        registry = ModelRegistry()
        file_path = tmp_model_dir / "old.bin"
        file_path.write_bytes(b"x" * 1024)
        model = ModelInfo(
            id="old",
            name="old",
            version="latest",
            modality="text",
            local_path=str(file_path.name),
        )
        registry.add_model(model)
        manager = StorageManager(model_path=tmp_model_dir, max_disk_gb=0.0000001)
        evicted = manager.enforce_storage_limit(registry)
        assert "old" in evicted
        assert registry.get_model("old").status == "evicted"

    def test_eviction_prefers_failed_downloads(self, tmp_model_dir, mock_registry):
        registry = ModelRegistry()
        failed_path = tmp_model_dir / "failed.bin"
        ok_path = tmp_model_dir / "ok.bin"
        failed_path.write_bytes(b"x" * 512)
        ok_path.write_bytes(b"x" * 512)
        failed = ModelInfo(
            id="failed",
            name="failed",
            version="latest",
            modality="text",
            local_path=str(failed_path.name),
            status="failed",
        )
        ok = ModelInfo(
            id="ok",
            name="ok",
            version="latest",
            modality="text",
            local_path=str(ok_path.name),
        )
        registry.add_model(failed)
        registry.add_model(ok)
        manager = StorageManager(model_path=tmp_model_dir, max_disk_gb=0.0000001)
        evicted = manager.enforce_storage_limit(registry)
        assert evicted[0] == "failed"
