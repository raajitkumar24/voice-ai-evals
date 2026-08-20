from __future__ import annotations

from typing import Any, Protocol

from voice_evals_schemas import ConversationTrace


class VoiceTraceConnector(Protocol):
    """Read-only boundary that normalizes external payloads before eval-core."""

    connector_id: str

    def normalize(self, payload: dict[str, Any]) -> ConversationTrace: ...


class CanonicalConnector:
    connector_id = "canonical-v1"

    def normalize(self, payload: dict[str, Any]) -> ConversationTrace:
        return ConversationTrace.model_validate(payload)
