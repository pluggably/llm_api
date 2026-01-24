from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from llm_api_client.errors import ApiError
from llm_api_client.models import (
    GenerateRequest,
    GenerateResponse,
    ModelCatalog,
    ModelDownloadRequest,
    ModelInfo,
    ProvidersResponse,
    Session,
    SessionList,
)


class SessionHandle:
    def __init__(self, client: "PluggablyClient", session_id: str) -> None:
        self._client = client
        self.session_id = session_id

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        return self._client.generate_with_session(self.session_id, request)

    def reset(self) -> Session:
        return self._client.reset_session(self.session_id)

    def close(self) -> Session:
        return self._client.close_session(self.session_id)


class PluggablyClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = client or httpx.Client(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _handle_error(self, response: httpx.Response) -> None:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        code = None
        message = response.text
        details = None
        if isinstance(payload, dict):
            if "detail" in payload and isinstance(payload["detail"], dict):
                code = payload["detail"].get("code")
                message = payload["detail"].get("message", message)
                details = payload["detail"].get("details")
            else:
                message = payload.get("message", message) if isinstance(payload, dict) else message
        raise ApiError(status_code=response.status_code, code=code, message=message, details=details)

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> httpx.Response:
        url = f"{self.base_url}{path}"
        response = self._client.request(method, url, headers=self._headers(), json=json_body)
        if response.status_code >= 400:
            self._handle_error(response)
        return response

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        response = self._request("POST", "/v1/generate", json_body=request.model_dump(mode="json"))
        return GenerateResponse.model_validate(response.json())

    def generate_with_session(self, session_id: str, request: GenerateRequest) -> GenerateResponse:
        payload = request.model_copy(update={"session_id": session_id}).model_dump(mode="json")
        response = self._request("POST", f"/v1/sessions/{session_id}/generate", json_body=payload)
        return GenerateResponse.model_validate(response.json())

    def list_models(self, modality: Optional[str] = None) -> ModelCatalog:
        path = "/v1/models"
        if modality:
            path = f"{path}?modality={modality}"
        response = self._request("GET", path)
        return ModelCatalog.model_validate(response.json())

    def get_model(self, model_id: str) -> ModelInfo:
        response = self._request("GET", f"/v1/models/{model_id}")
        return ModelInfo.model_validate(response.json())

    def list_providers(self) -> ProvidersResponse:
        response = self._request("GET", "/v1/providers")
        return ProvidersResponse.model_validate(response.json())

    def get_schema(self) -> Dict[str, Any]:
        response = self._request("GET", "/v1/schema")
        return response.json()

    def download_model(self, request: ModelDownloadRequest) -> Dict[str, Any]:
        response = self._request("POST", "/v1/models/download", json_body=request.model_dump(mode="json"))
        return response.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        response = self._request("GET", f"/v1/jobs/{job_id}")
        return response.json()

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        response = self._request("DELETE", f"/v1/jobs/{job_id}")
        return response.json()

    def create_session(self) -> Session:
        response = self._request("POST", "/v1/sessions")
        return Session.model_validate(response.json())

    def list_sessions(self) -> SessionList:
        response = self._request("GET", "/v1/sessions")
        return SessionList.model_validate(response.json())

    def get_session(self, session_id: str) -> Session:
        response = self._request("GET", f"/v1/sessions/{session_id}")
        return Session.model_validate(response.json())

    def reset_session(self, session_id: str) -> Session:
        response = self._request("POST", f"/v1/sessions/{session_id}/reset")
        return Session.model_validate(response.json())

    def close_session(self, session_id: str) -> Session:
        response = self._request("DELETE", f"/v1/sessions/{session_id}")
        return Session.model_validate(response.json())

    def session(self, session_id: str) -> SessionHandle:
        return SessionHandle(self, session_id)
