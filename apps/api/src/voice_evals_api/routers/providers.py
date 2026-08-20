from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from voice_evals_llm_gateway import ProviderError

from ..config import Settings, get_settings
from ..db import get_db
from ..models import AuditEvent, ProviderConnection
from ..security import Principal, SecretCipher, require_user
from ..services.provider_runtime import environment_secret, provider_for_record

router = APIRouter(prefix="/providers", tags=["providers"])
ProviderKind = Literal["openai", "anthropic", "gemini", "openai-compatible", "ollama", "test"]
SecretSource = Literal["ENCRYPTED_DB", "ENVIRONMENT", "NONE"]


class ProviderConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider: ProviderKind
    base_url: HttpUrl | None = None
    default_model: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    secret_source: SecretSource = "ENCRYPTED_DB"
    capability_overrides: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_secret_mode(self) -> ProviderConnectionCreate:
        if self.secret_source == "ENVIRONMENT" and self.api_key:
            raise ValueError("Do not send an API key when using environment credential mode")
        if self.provider == "ollama" and self.secret_source == "ENCRYPTED_DB" and not self.api_key:
            self.secret_source = "NONE"
        if self.provider == "test":
            self.secret_source = "NONE"
        return self


class ProviderConnectionView(BaseModel):
    id: str
    name: str
    provider: str
    base_url: str | None
    default_model: str | None
    secret_source: str
    credential_configured: bool
    capability_overrides: dict[str, Any]
    status: str
    last_tested_at: datetime | None


class ProviderConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: HttpUrl | None = None
    default_model: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    capability_overrides: dict[str, bool] | None = None


def provider_view(record: ProviderConnection) -> ProviderConnectionView:
    configured = record.secret_source in {"ENVIRONMENT", "NONE"} or bool(record.secret_ciphertext)
    return ProviderConnectionView(
        id=record.id,
        name=record.name,
        provider=record.provider,
        base_url=record.base_url,
        default_model=record.default_model,
        secret_source=record.secret_source,
        credential_configured=configured,
        capability_overrides=record.capability_overrides,
        status=record.status,
        last_tested_at=record.last_tested_at,
    )


@router.post("", response_model=ProviderConnectionView, status_code=status.HTTP_201_CREATED)
def create_provider_connection(
    payload: ProviderConnectionCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProviderConnectionView:
    if payload.provider == "test" and not settings.enable_test_provider:
        raise HTTPException(status_code=403, detail="Test provider is disabled")
    ciphertext: str | None = None
    if payload.secret_source == "ENCRYPTED_DB":
        if not payload.api_key:
            raise HTTPException(status_code=422, detail="An API key is required")
        try:
            ciphertext = SecretCipher(settings.encryption_key).encrypt(payload.api_key)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail="Credential encryption is not configured on this deployment",
            ) from exc
    elif payload.secret_source == "ENVIRONMENT" and not environment_secret(payload.provider):
        raise HTTPException(status_code=422, detail="Provider environment credential is not set")
    record = ProviderConnection(
        workspace_id=principal.workspace_id,
        name=payload.name,
        provider=payload.provider,
        base_url=str(payload.base_url).rstrip("/") if payload.base_url else None,
        default_model=payload.default_model,
        secret_ciphertext=ciphertext,
        secret_source=payload.secret_source,
        capability_overrides=payload.capability_overrides,
    )
    db.add(record)
    db.flush()
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="provider_connection.created",
            entity_type="provider_connection",
            entity_id=record.id,
            event_data={"provider": record.provider, "secret_source": record.secret_source},
        )
    )
    db.commit()
    db.refresh(record)
    return provider_view(record)


@router.get("", response_model=list[ProviderConnectionView])
def list_provider_connections(
    principal: Principal = Depends(require_user), db: Session = Depends(get_db)
) -> list[ProviderConnectionView]:
    records = db.scalars(
        select(ProviderConnection)
        .where(ProviderConnection.workspace_id == principal.workspace_id)
        .order_by(ProviderConnection.created_at)
    ).all()
    return [provider_view(record) for record in records]


def _get_connection(db: Session, workspace_id: str, connection_id: str) -> ProviderConnection:
    record = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.id == connection_id,
            ProviderConnection.workspace_id == workspace_id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="Provider connection not found")
    return record


@router.put("/{connection_id}", response_model=ProviderConnectionView)
def update_provider_connection(
    connection_id: str,
    payload: ProviderConnectionUpdate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProviderConnectionView:
    record = _get_connection(db, principal.workspace_id, connection_id)
    if payload.name is not None:
        record.name = payload.name
    if payload.base_url is not None:
        record.base_url = str(payload.base_url).rstrip("/")
    if payload.default_model is not None:
        record.default_model = payload.default_model
    if payload.capability_overrides is not None:
        record.capability_overrides = payload.capability_overrides
    if payload.api_key is not None:
        if record.secret_source != "ENCRYPTED_DB":
            raise HTTPException(
                status_code=409,
                detail="Only encrypted-database connections accept credential rotation",
            )
        try:
            record.secret_ciphertext = SecretCipher(settings.encryption_key).encrypt(
                payload.api_key
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503, detail="Credential encryption is unavailable"
            ) from exc
    record.status = "UNTESTED"
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="provider_connection.updated",
            entity_type="provider_connection",
            entity_id=record.id,
            event_data={"credential_rotated": payload.api_key is not None},
        )
    )
    db.commit()
    db.refresh(record)
    return provider_view(record)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_connection(
    connection_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> None:
    record = _get_connection(db, principal.workspace_id, connection_id)
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="provider_connection.deleted",
            entity_type="provider_connection",
            entity_id=record.id,
            event_data={"provider": record.provider},
        )
    )
    db.delete(record)
    db.commit()


@router.post("/{connection_id}/test", response_model=dict[str, Any])
async def test_provider_connection(
    connection_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    record = _get_connection(db, principal.workspace_id, connection_id)
    try:
        health = await provider_for_record(record, settings).test_connection()
    except (ProviderError, RuntimeError) as exc:
        record.status = "ERROR"
        record.last_tested_at = datetime.now(UTC)
        db.add(
            AuditEvent(
                workspace_id=principal.workspace_id,
                actor_user_id=principal.user_id,
                event_type="provider_connection.tested",
                entity_type="provider_connection",
                entity_id=record.id,
                event_data={"provider": record.provider, "status": "ERROR"},
            )
        )
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record.status = "CONNECTED"
    record.last_tested_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="provider_connection.tested",
            entity_type="provider_connection",
            entity_id=record.id,
            event_data={"provider": record.provider, "status": "CONNECTED"},
        )
    )
    db.commit()
    return dict(health.model_dump(mode="json"))


@router.get("/{connection_id}/models", response_model=list[dict[str, Any]])
async def list_provider_models(
    connection_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    record = _get_connection(db, principal.workspace_id, connection_id)
    try:
        models = await provider_for_record(record, settings).list_models()
    except (ProviderError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [model.model_dump(mode="json") for model in models]
