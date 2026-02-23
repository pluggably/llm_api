"""TEST-SYS-003: Model download job workflow
Traceability: SYS-REQ-010, SYS-REQ-013
"""
class TestModelDownloadWorkflow:
    """System tests for model download workflow."""

    def test_start_download_returns_job_id(self, client):
        payload = {
            "model": {"id": "m1", "name": "m1", "version": "latest", "modality": "text"},
            "source": {"type": "local", "uri": "./models/m1"},
        }
        response = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 202
        assert response.json()["job_id"]

    def test_job_status_shows_progress(self, client, running_download_job):
        response = client.get(f"/v1/jobs/{running_download_job}", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["progress_pct"] >= 0

    def test_completed_download_available_in_registry(self, client, completed_download):
        response = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert any(m["id"] == "model-complete" for m in response.json()["models"])

    def test_failed_download_shows_error(self, client, failed_download_job):
        response = client.get(f"/v1/jobs/{failed_download_job}", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "failed"
        assert body["error"]

    def test_cancel_download_job(self, client, running_download_job):
        response = client.delete(f"/v1/jobs/{running_download_job}", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_duplicate_download_reuses_existing(self, client):
        payload = {
            "model": {"id": "dup", "name": "dup", "version": "latest", "modality": "text"},
            "source": {"type": "local", "uri": "./models/dup"},
        }
        first = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
        second = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
        assert first.status_code == 202
        assert second.status_code == 202

    def test_add_hf_hosted_model_without_local_download(self, client):
        payload = {
            "model": {
                "id": "meta-llama/Llama-3.2-1B-Instruct",
                "name": "meta-llama/Llama-3.2-1B-Instruct",
                "version": "latest",
                "modality": "text",
                "provider": "huggingface",
            },
            "source": {
                "type": "huggingface",
                "id": "meta-llama/Llama-3.2-1B-Instruct",
            },
            "options": {
                "install_local": False,
            },
        }

        response = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 202
        assert response.json()["status"] == "completed"

        models_resp = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert models_resp.status_code == 200
        hosted = [m for m in models_resp.json()["models"] if m["id"] == "meta-llama/Llama-3.2-1B-Instruct"]
        assert hosted
        assert hosted[0]["provider"] == "huggingface"
        assert hosted[0]["local_path"] is None
