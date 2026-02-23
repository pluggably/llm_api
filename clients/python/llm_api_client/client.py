from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional

import httpx

from llm_api_client.errors import ApiError
from llm_api_client.models import (
    GenerateRequest,
    GenerateResponse,
    LoadedModelsResponse,
    ModelInfo,
    ModelRuntimeStatus,
    ModelSchema,
    ModelSearchResponse,
    ModelCatalog,
    ModelDownloadRequest,
    DownloadJobStatus,
    ProviderKeyInfo,
    QueuePositionResponse,
    CancelRequestResponse,
    RegenerateRequest,
    TokenCreatedResponse,
    TokenInfo,
    UserLoginResponse,
    UserProfile,
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

    def generate_stream_events(self, request: GenerateRequest) -> Iterator[Dict[str, Any]]:
        """Stream generation events.

        Yields dicts with type: model_selected, text, complete.
        """
        return self._stream_events("/v1/generate", request.model_dump(mode="json"))

    def generate_with_session(self, session_id: str, request: GenerateRequest) -> GenerateResponse:
        payload = request.model_copy(update={"session_id": session_id}).model_dump(mode="json")
        response = self._request("POST", f"/v1/sessions/{session_id}/generate", json_body=payload)
        return GenerateResponse.model_validate(response.json())

    def regenerate(self, session_id: str, request: RegenerateRequest) -> GenerateResponse:
        response = self._request(
            "POST",
            f"/v1/sessions/{session_id}/regenerate",
            json_body=request.model_dump(mode="json"),
        )
        return GenerateResponse.model_validate(response.json())

    def regenerate_stream(self, session_id: str, request: RegenerateRequest) -> Iterator[Dict[str, Any]]:
        return self._stream_events(
            f"/v1/sessions/{session_id}/regenerate",
            request.model_dump(mode="json"),
        )

    def list_models(self, modality: Optional[str] = None) -> ModelCatalog:
        path = "/v1/models"
        if modality:
            path = f"{path}?modality={modality}"
        response = self._request("GET", path)
        return ModelCatalog.model_validate(response.json())

    def search_models(
        self,
        query: str,
        source: str = "huggingface",
        modality: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ModelSearchResponse:
        params = [f"query={query}", f"source={source}"]
        if modality:
            params.append(f"modality={modality}")
        if cursor:
            params.append(f"cursor={cursor}")
        if limit is not None:
            params.append(f"limit={limit}")
        path = "/v1/models/search?" + "&".join(params)
        response = self._request("GET", path)
        return ModelSearchResponse.model_validate(response.json())

    def get_model(self, model_id: str) -> ModelInfo:
        response = self._request("GET", f"/v1/models/{model_id}")
        return ModelInfo.model_validate(response.json())

    def set_default_model(self, model_id: str) -> ModelInfo:
        response = self._request("POST", f"/v1/models/{model_id}/default", json_body={})
        return ModelInfo.model_validate(response.json())

    def list_providers(self) -> ProvidersResponse:
        response = self._request("GET", "/v1/providers")
        return ProvidersResponse.model_validate(response.json())

    def get_schema(self, model_id: Optional[str] = None) -> ModelSchema | Dict[str, Any]:
        path = "/v1/schema"
        if model_id:
            path = f"{path}?model={model_id}"
        response = self._request("GET", path)
        payload = response.json()
        if model_id:
            properties = payload.get("properties") or {}
            parameters = {}
            for name, entry in properties.items():
                parameters[name] = {
                    "name": name,
                    "type": entry.get("type"),
                    "title": entry.get("title"),
                    "description": entry.get("description"),
                    "default": entry.get("default"),
                    "minimum": entry.get("minimum"),
                    "maximum": entry.get("maximum"),
                    "enum": entry.get("enum"),
                }
            return ModelSchema.model_validate(
                {
                    "model_id": payload.get("model_id", model_id),
                    "version": payload.get("version"),
                    "parameters": parameters,
                }
            )
        return payload

    def download_model(self, request: ModelDownloadRequest) -> Dict[str, Any]:
        response = self._request("POST", "/v1/models/download", json_body=request.model_dump(mode="json"))
        return response.json()

    def get_model_status(self, model_id: str) -> ModelRuntimeStatus:
        response = self._request("GET", f"/v1/models/{model_id}/status")
        return ModelRuntimeStatus.model_validate(response.json())

    def load_model(
        self,
        model_id: str,
        wait: bool = False,
        use_fallback: bool = False,
        fallback_model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "wait": wait,
            "use_fallback": use_fallback,
        }
        if fallback_model_id:
            body["fallback_model_id"] = fallback_model_id
        response = self._request("POST", f"/v1/models/{model_id}/load", json_body=body)
        return response.json()

    def unload_model(self, model_id: str, force: bool = False) -> Dict[str, Any]:
        response = self._request("POST", f"/v1/models/{model_id}/unload?force={str(force).lower()}")
        return response.json()

    def get_loaded_models(self) -> LoadedModelsResponse:
        response = self._request("GET", "/v1/models/loaded")
        return LoadedModelsResponse.model_validate(response.json())

    def get_job(self, job_id: str) -> Dict[str, Any]:
        response = self._request("GET", f"/v1/jobs/{job_id}")
        return response.json()

    def list_jobs(self) -> List[DownloadJobStatus]:
        response = self._request("GET", "/v1/jobs")
        payload = response.json()
        jobs = payload.get("jobs") if isinstance(payload, dict) else payload
        return [DownloadJobStatus.model_validate(job) for job in (jobs or [])]

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        response = self._request("DELETE", f"/v1/jobs/{job_id}")
        return response.json()

    def get_request_status(self, request_id: str) -> QueuePositionResponse:
        response = self._request("GET", f"/v1/requests/{request_id}/status")
        return QueuePositionResponse.model_validate(response.json())

    def cancel_request(self, request_id: str) -> CancelRequestResponse:
        response = self._request("POST", f"/v1/requests/{request_id}/cancel")
        return CancelRequestResponse.model_validate(response.json())

    def create_session(self, title: Optional[str] = None) -> Session:
        response = self._request("POST", "/v1/sessions", json_body={"title": title} if title else None)
        return Session.model_validate(response.json())

    def list_sessions(self) -> SessionList:
        response = self._request("GET", "/v1/sessions")
        return SessionList.model_validate(response.json())

    def get_session(self, session_id: str) -> Session:
        response = self._request("GET", f"/v1/sessions/{session_id}")
        return Session.model_validate(response.json())

    def update_session(self, session_id: str, title: Optional[str] = None) -> Session:
        response = self._request(
            "PUT",
            f"/v1/sessions/{session_id}",
            json_body={"title": title} if title is not None else {},
        )
        return Session.model_validate(response.json())

    def reset_session(self, session_id: str) -> Session:
        response = self._request("POST", f"/v1/sessions/{session_id}/reset")
        return Session.model_validate(response.json())

    def close_session(self, session_id: str) -> Session:
        response = self._request("DELETE", f"/v1/sessions/{session_id}")
        return Session.model_validate(response.json())

    def delete_session(self, session_id: str) -> Session:
        return self.close_session(session_id)

    def session(self, session_id: str) -> SessionHandle:
        return SessionHandle(self, session_id)

    def register(self, email: str, password: str, invite_token: Optional[str] = None) -> UserProfile:
        body = {"email": email, "password": password}
        if invite_token:
            body["invite_token"] = invite_token
        response = self._request("POST", "/v1/users/register", json_body=body)
        return UserProfile.model_validate(response.json())

    def login(self, email: str, password: str) -> UserLoginResponse:
        response = self._request(
            "POST",
            "/v1/users/login",
            json_body={"email": email, "password": password},
        )
        return UserLoginResponse.model_validate(response.json())

    def get_profile(self) -> UserProfile:
        response = self._request("GET", "/v1/users/me")
        return UserProfile.model_validate(response.json())

    def update_profile(
        self,
        display_name: Optional[str] = None,
        preferred_model: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> UserProfile:
        body: Dict[str, Any] = {}
        if display_name is not None:
            body["display_name"] = display_name
        if preferred_model is not None:
            body["preferred_model"] = preferred_model
        if preferences is not None:
            body["preferences"] = preferences
        response = self._request("PATCH", "/v1/users/me", json_body=body)
        return UserProfile.model_validate(response.json())

    def list_user_tokens(self) -> List[TokenInfo]:
        response = self._request("GET", "/v1/users/tokens")
        payload = response.json()
        tokens = payload if isinstance(payload, list) else []
        return [TokenInfo.model_validate(token) for token in tokens]

    def create_user_token(self, name: Optional[str] = None) -> TokenCreatedResponse:
        response = self._request(
            "POST",
            "/v1/users/tokens",
            json_body={"name": name} if name else {},
        )
        return TokenCreatedResponse.model_validate(response.json())

    def revoke_user_token(self, token_id: str) -> Dict[str, Any]:
        response = self._request("DELETE", f"/v1/users/tokens/{token_id}")
        return response.json()

    def list_provider_keys(self) -> List[ProviderKeyInfo]:
        response = self._request("GET", "/v1/users/provider-keys")
        payload = response.json()
        keys = payload if isinstance(payload, list) else []
        return [ProviderKeyInfo.model_validate(item) for item in keys]

    def add_provider_key(
        self,
        provider: str,
        credential_type: str = "api_key",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        oauth_token: Optional[str] = None,
        service_account_json: Optional[str] = None,
    ) -> ProviderKeyInfo:
        body: Dict[str, Any] = {
            "provider": provider,
            "credential_type": credential_type,
        }
        if api_key is not None:
            body["api_key"] = api_key
        if endpoint is not None:
            body["endpoint"] = endpoint
        if oauth_token is not None:
            body["oauth_token"] = oauth_token
        if service_account_json is not None:
            body["service_account_json"] = service_account_json
        response = self._request("POST", "/v1/users/provider-keys", json_body=body)
        return ProviderKeyInfo.model_validate(response.json())

    def remove_provider_key(self, provider: str) -> Dict[str, Any]:
        response = self._request("DELETE", f"/v1/users/provider-keys/{provider}")
        return response.json()

    def get_health(self) -> Dict[str, Any]:
        response = self._request("GET", "/health")
        return response.json()

    def close(self) -> None:
        self._client.close()

    def _stream_events(self, path: str, json_body: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        with self._client.stream("POST", url, headers=self._headers(), json=json_body) as response:
            if response.status_code >= 400:
                self._handle_error(response)

            for line in response.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    return
                try:
                    payload = json.loads(data)
                except Exception:
                    continue

                if isinstance(payload, dict):
                    if payload.get("event") == "model_selected":
                        yield {
                            "type": "model_selected",
                            "model_id": payload.get("model"),
                            "model_name": payload.get("model_name"),
                        }
                        continue
                    if payload.get("error") is not None:
                        raise ApiError(status_code=500, code="stream_error", message=str(payload.get("error")))
                    if payload.get("output") is not None or payload.get("modality") is not None:
                        yield {
                            "type": "complete",
                            "response": GenerateResponse.model_validate(payload),
                        }
                        continue
                    if payload.get("choices") is not None:
                        content = None
                        try:
                            content = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                        except Exception:
                            content = None
                        if content:
                            yield {"type": "text", "content": content}
