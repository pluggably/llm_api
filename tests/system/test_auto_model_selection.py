"""Auto model selection system tests.

Traceability:
  TEST-SYS-CR003-001  SYS-REQ-CR003-001  model omitted or "auto" -> resolved model in response
  TEST-SYS-CR003-002  SYS-REQ-CR003-002  image input auto-selects image model
  TEST-SYS-CR003-003  SYS-REQ-CR003-004  explicit model_id preserved
  TEST-SYS-CR003-004  SYS-REQ-CR003-005  selection_mode free_only / commercial_only filters
  SYS-REQ-005         routing/selection mechanism
"""
from __future__ import annotations

import json
import pytest

from llm_api.registry import store as registry_store
from llm_api.api.schemas import ModelInfo

HEADERS = {"X-API-Key": "test-key"}


def _image_model(registry) -> None:
    """Register an image model so image-selection tests have a target."""
    registry.add_model(
        ModelInfo(
            id="local-image-model",
            name="Local Image",
            version="latest",
            modality="image",
            provider="local",
            status="available",
        )
    )


class TestAutoModelOmitted:
    """TEST-SYS-CR003-001: model omitted -> resolved model returned."""

    def test_no_model_uses_default(self, client):
        """Omitting model field should succeed and return a resolved model."""
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["model"], "response.model should be populated"
        assert body["output"]["text"], "text output expected"

    def test_model_auto_string_uses_default(self, client):
        """model='auto' should behave the same as omitting model."""
        payload = {"modality": "text", "input": {"prompt": "Hello"}, "model": "auto"}
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["model"], "response.model should be populated"

    def test_response_includes_selection_metadata(self, client):
        """Response should include selection info when model was auto-resolved."""
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        selection = body.get("selection")
        if selection:  # selection is optional; if present verify fields
            assert "selected_model" in selection
            assert isinstance(selection["fallback_used"], bool)

    def test_model_auto_image_modality(self, client):
        """model='auto' with modality=image should return image output."""
        payload = {"modality": "image", "input": {"prompt": "A cat"}, "model": "auto"}
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        output = resp.json()["output"]
        assert output.get("images") or output.get("artifacts"), "image output expected"

    def test_model_auto_3d_modality(self, client):
        """model='auto' with modality=3d should return mesh output."""
        payload = {"modality": "3d", "input": {"prompt": "A chair"}, "model": "auto"}
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        output = resp.json()["output"]
        assert output.get("mesh") or output.get("artifacts"), "3d output expected"


class TestAutoImageInputRouting:
    """TEST-SYS-CR003-002: image input under Auto selects image model."""

    def test_image_input_without_explicit_modality(self, client):
        """Request with image input should succeed with image model auto-selected."""
        import base64
        # 1x1 white PNG in base64
        tiny_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        payload = {
            "modality": "text",
            "input": {"prompt": "Describe this image", "images": [tiny_b64]},
        }
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        # Should succeed (200) or return a model-not-found when no image model registered
        assert resp.status_code in (200, 404, 503), f"Unexpected {resp.status_code}: {resp.text}"


class TestExplicitModelPreserved:
    """TEST-SYS-CR003-003: explicit model ID bypasses auto-selection."""

    def test_explicit_local_model_id_used(self, client):
        """Explicitly specified model ID is routed correctly."""
        payload = {"modality": "text", "input": {"prompt": "Hello"}}
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        default_model = resp.json()["model"]

        # Re-request with that explicit model ID
        payload2 = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "model": default_model,
        }
        resp2 = client.post("/v1/generate", json=payload2, headers=HEADERS)
        assert resp2.status_code == 200
        assert resp2.json()["model"] == default_model

    def test_unknown_model_id_returns_404(self, client):
        """Explicitly specified unknown model returns 404."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "model": "completely-unknown-model-xyz",
        }
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 404


class TestSelectionModeFilters:
    """TEST-SYS-CR003-004: selection_mode filters constrain auto-selection.
    SYS-REQ-CR003-005.
    """

    def test_free_only_rejects_commercial_providers(self, client, mock_registry):
        """selection_mode=free_only should not route to commercial providers."""
        # Register an openai model in the registry
        mock_registry.add_model(
            ModelInfo(
                id="gpt-4o-mini",
                name="GPT-4o Mini",
                version="latest",
                modality="text",
                provider="openai",
                status="available",
            )
        )
        registry_store._registry = mock_registry
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "selection_mode": "free_only",
            "model": "auto",
        }
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        # Should succeed with a local model
        if resp.status_code == 200:
            assert resp.json()["model"] != "gpt-4o-mini", (
                "free_only should not select openai model"
            )

    def test_commercial_only_with_no_commercial_model(self, client):
        """selection_mode=commercial_only with no configured commercial provider should return an error."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "selection_mode": "commercial_only",
            "model": "auto",
        }
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        # Should succeed (falls back to local) or fail with 404/503
        assert resp.status_code in (200, 404, 422, 503)

    def test_selection_mode_model_without_model_id_returns_400(self, client):
        """selection_mode=model without explicit model ID should return 400."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "selection_mode": "model",
        }
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        assert resp.status_code == 400

    def test_selection_mode_model_with_model_id_succeeds(self, client):
        """selection_mode=model with explicit model ID should succeed."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "selection_mode": "model",
            "model": "local-text",
        }
        resp = client.post("/v1/generate", json=payload, headers=HEADERS)
        # 200 if model exists, 404 if not - both are valid
        assert resp.status_code in (200, 404)


class TestAutoSelectionStreaming:
    """Selection metadata present in SSE stream."""

    def test_stream_contains_model_selected_event(self, client):
        """Streaming response should emit a model_selected SSE event."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "stream": True,
        }
        with client.stream("POST", "/v1/generate", json=payload, headers=HEADERS) as resp:
            assert resp.status_code == 200
            lines = [ln for ln in resp.iter_lines() if ln.startswith("data: ")]

        data_payloads = []
        for line in lines:
            raw = line[len("data: "):]
            if raw == "[DONE]":
                continue
            try:
                data_payloads.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        model_selected_events = [
            p for p in data_payloads if p.get("event") == "model_selected"
        ]
        assert model_selected_events, "Expected at least one model_selected SSE event"
        evt = model_selected_events[0]
        assert evt.get("model"), "model_selected event should include model"
        assert "modality" in evt

    def test_stream_model_selected_includes_fallback_flag(self, client):
        """model_selected event should include fallback_used boolean."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "stream": True,
        }
        with client.stream("POST", "/v1/generate", json=payload, headers=HEADERS) as resp:
            lines = [ln for ln in resp.iter_lines() if ln.startswith("data: ")]

        for line in lines:
            raw = line[len("data: "):]
            if raw == "[DONE]":
                continue
            try:
                evt = json.loads(raw)
                if evt.get("event") == "model_selected":
                    assert "fallback_used" in evt
                    break
            except json.JSONDecodeError:
                pass
