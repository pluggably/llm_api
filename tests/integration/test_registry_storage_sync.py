"""TEST-INT-002: Registry and storage synchronization
Traceability: SYS-REQ-012
"""
from llm_api.api.schemas import ModelInfo
from llm_api.registry.store import ModelRegistry
from llm_api.storage.manager import StorageManager


class TestRegistryStorageSync:
    """Integration tests for registry and storage synchronization."""

    def test_registry_updates_on_storage_eviction(self, tmp_model_dir, mock_registry):
        registry = ModelRegistry()
        model_path = tmp_model_dir / "evict.bin"
        model_path.write_bytes(b"x" * 1024)
        model = ModelInfo(
            id="evict",
            name="evict",
            version="latest",
            modality="text",
            local_path=model_path.name,
        )
        registry.add_model(model)
        manager = StorageManager(model_path=tmp_model_dir, max_disk_gb=0.0000001)
        manager.enforce_storage_limit(registry)
        assert registry.get_model("evict").status == "evicted"

    def test_download_creates_registry_entry(self, tmp_model_dir, mock_registry):
        registry = ModelRegistry()
        model = ModelInfo(
            id="download",
            name="download",
            version="latest",
            modality="text",
            status="downloading",
        )
        registry.add_model(model)
        assert registry.get_model("download").status == "downloading"
        registry.update_model_status("download", "available")
        assert registry.get_model("download").status == "available"

    def test_failed_download_updates_registry(self, tmp_model_dir, mock_registry):
        registry = ModelRegistry()
        model = ModelInfo(
            id="fail",
            name="fail",
            version="latest",
            modality="text",
            status="downloading",
        )
        registry.add_model(model)
        registry.update_model_status("fail", "failed")
        assert registry.get_model("fail").status == "failed"

    def test_registry_reflects_storage_reality(self, tmp_model_dir, mock_registry):
        registry = ModelRegistry()
        model_path = tmp_model_dir / "missing.bin"
        model_path.write_bytes(b"x")
        model = ModelInfo(
            id="missing",
            name="missing",
            version="latest",
            modality="text",
            local_path=model_path.name,
        )
        registry.add_model(model)
        model_path.unlink()
        registry.sync_with_storage(tmp_model_dir)
        assert registry.get_model("missing").status == "evicted"
