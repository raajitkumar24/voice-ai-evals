from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

import httpx
from voice_evals_schemas import ConversationTrace


class VoiceEvalsError(RuntimeError):
    pass


class VoiceEvalsClient:
    """Synchronous client for workspace-scoped Voice AI Evals APIs."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        *,
        timeout: float = 30,
        transport: httpx.BaseTransport | None = None,
    ):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> VoiceEvalsClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self._dict_request(
            "POST", "/api/v1/auth/login", json={"email": email, "password": password}
        )

    def upsert_agent(
        self, external_id: str, name: str, description: str | None = None
    ) -> dict[str, Any]:
        return self._dict_request(
            "PUT",
            f"/api/v1/agents/{external_id}",
            json={"external_id": external_id, "name": name, "description": description},
        )

    def upsert_agent_configuration(
        self, agent_id: str, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        config_id = str(configuration["id"])
        return self._dict_request(
            "PUT",
            f"/api/v1/agents/{agent_id}/configurations/{config_id}",
            json=configuration,
        )

    def upsert_tool_definition(self, definition: dict[str, Any]) -> dict[str, Any]:
        return self._dict_request(
            "PUT",
            f"/api/v1/tool-definitions/{definition['id']}",
            json=definition,
        )

    def upsert_knowledge_source(self, source: dict[str, Any]) -> dict[str, Any]:
        return self._dict_request(
            "PUT",
            f"/api/v1/knowledge-sources/{source['external_id']}",
            json=source,
        )

    def ingest_conversation(
        self, trace: ConversationTrace | dict[str, Any], idempotency_key: str | None = None
    ) -> dict[str, Any]:
        validated = (
            trace
            if isinstance(trace, ConversationTrace)
            else ConversationTrace.model_validate(trace)
        )
        body = validated.model_dump(mode="json")
        key = idempotency_key or hashlib.sha256(validated.model_dump_json().encode()).hexdigest()
        return self._dict_request(
            "POST",
            "/api/v1/ingestion/conversations",
            json=body,
            headers={"Idempotency-Key": key},
        )

    def ingest_batch(self, traces: Iterable[ConversationTrace | dict[str, Any]]) -> dict[str, Any]:
        items = [
            item.model_dump(mode="json")
            if isinstance(item, ConversationTrace)
            else ConversationTrace.model_validate(item).model_dump(mode="json")
            for item in traces
        ]
        payload_hash = hashlib.sha256(
            "".join(sorted(str(item["conversation_id"]) for item in items)).encode()
        ).hexdigest()
        return self._dict_request(
            "POST",
            "/api/v1/ingestion/conversations/batch",
            json={"items": items},
            headers={"Idempotency-Key": payload_hash},
        )

    def create_eval_run(
        self,
        conversation_ids: list[str],
        provider_connection_id: str,
        model: str,
        suite_id: str | None = None,
    ) -> dict[str, Any]:
        return self._dict_request(
            "POST",
            "/api/v1/eval-runs",
            json={
                "conversation_ids": conversation_ids,
                "provider_connection_id": provider_connection_id,
                "model": model,
                "suite_id": suite_id,
            },
        )

    def list_findings(self) -> list[dict[str, Any]]:
        result = self._request("GET", "/api/v1/findings")
        if not isinstance(result, list):
            raise VoiceEvalsError("Expected a list of findings")
        return result

    def _dict_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        result = self._request(method, path, **kwargs)
        if not isinstance(result, dict):
            raise VoiceEvalsError(f"Expected an object response from {method} {path}")
        return result

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            csrf = self._http.cookies.get("voice_evals_csrf")
            if csrf:
                headers = dict(kwargs.pop("headers", {}))
                headers["X-CSRF-Token"] = csrf
                kwargs["headers"] = headers
        response = self._http.request(method, path, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise VoiceEvalsError(
                f"{method} {path} failed ({response.status_code}): {detail}"
            ) from exc
        if response.status_code == 204:
            return None
        return response.json()
