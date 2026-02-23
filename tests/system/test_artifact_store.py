"""
TEST-SYS-006: Artifact store output
Traceability: SYS-REQ-016
"""
from llm_api.storage import artifact_store


class TestArtifactStore:
    """System tests for artifact store and large output handling."""

    def test_image_output_returns_artifact_url(self, client_factory):
        client = client_factory({"artifact_inline_threshold_kb": "0"})
        payload = {"modality": "image", "input": {"prompt": "A cat"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        artifacts = response.json()["output"]["artifacts"]
        url = artifacts[0]["url"]
        assert "/v1/artifacts/" in url

    def test_artifact_url_is_downloadable(self, client_factory):
        client = client_factory({"artifact_inline_threshold_kb": "0"})
        payload = {"modality": "image", "input": {"prompt": "A cat"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        artifact_url = response.json()["output"]["artifacts"][0]["url"]
        # CR-002: URLs are now absolute; strip base for TestClient
        if artifact_url.startswith("http"):
            from urllib.parse import urlparse
            artifact_url = urlparse(artifact_url).path
        fetch = client.get(artifact_url)
        assert fetch.status_code == 200
        # Artifact endpoint returns raw bytes with appropriate content-type
        assert len(fetch.content) > 0

    def test_artifact_url_expires(self, client_factory):
        client = client_factory({"artifact_inline_threshold_kb": "0"})
        payload = {"modality": "image", "input": {"prompt": "A cat"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        artifact_id = response.json()["output"]["artifacts"][0]["id"]
        store = artifact_store.get_artifact_store()
        store.artifacts[artifact_id].expires_at = artifact_store.now().replace(year=2000)
        fetch = client.get(f"/v1/artifacts/{artifact_id}")
        assert fetch.status_code == 410

    def test_3d_output_returns_artifact_url(self, client_factory):
        client = client_factory({"artifact_inline_threshold_kb": "0"})
        payload = {"modality": "3d", "input": {"prompt": "A chair"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        artifacts = response.json()["output"]["artifacts"]
        url = artifacts[0]["url"]
        assert "/v1/artifacts/" in url

    def test_small_text_output_inline(self, client):
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        response = client.post("/v1/generate", json=payload, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        output = response.json()["output"]
        assert output.get("text")
        assert not output.get("artifacts")
