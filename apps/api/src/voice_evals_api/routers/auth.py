import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import (
    AuditEvent,
    AuthSession,
    User,
    Workspace,
    WorkspaceApiKey,
    WorkspaceMembership,
)
from ..security import (
    Principal,
    create_api_key,
    create_db_session,
    digest_token,
    require_user,
    verify_password,
)
from ..services.rate_limit import login_rate_limit

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=512)
    workspace_id: str | None = None


class UserView(BaseModel):
    id: str
    email: str
    workspace_id: str


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    prefix: str
    key: str
    warning: str = "Store this key now. It will not be shown again."


@router.post("/login", response_model=UserView)
def login(
    payload: LoginRequest,
    response: Response,
    _: None = Depends(login_rate_limit),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserView:
    user = db.scalar(
        select(User).where(User.email == payload.email.lower(), User.is_active.is_(True))
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    workspace_query = (
        select(Workspace)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == user.id)
    )
    if payload.workspace_id:
        workspace_query = workspace_query.where(Workspace.id == payload.workspace_id)
    workspace = db.scalar(workspace_query.limit(1))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace available")
    token = create_db_session(db, user, workspace.id, settings)
    response.set_cookie(
        "voice_evals_session",
        token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    response.set_cookie(
        "voice_evals_csrf",
        secrets.token_urlsafe(32),
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return UserView(id=user.id, email=user.email, workspace_id=workspace.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias="voice_evals_session"),
) -> Response:
    if session_token:
        auth_session = db.scalar(
            select(AuthSession).where(AuthSession.token_hash == digest_token(session_token))
        )
        if auth_session:
            db.delete(auth_session)
            db.commit()
    response.delete_cookie("voice_evals_session", path="/")
    response.delete_cookie("voice_evals_csrf", path="/")
    return response


@router.get("/me", response_model=UserView)
def me(principal: Principal = Depends(require_user), db: Session = Depends(get_db)) -> UserView:
    user = db.get(User, principal.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )
    return UserView(id=user.id, email=user.email, workspace_id=principal.workspace_id)


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def issue_api_key(
    payload: ApiKeyCreate,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreated:
    raw, prefix = create_api_key()
    record = WorkspaceApiKey(
        workspace_id=principal.workspace_id,
        name=payload.name,
        prefix=prefix,
        key_hash=digest_token(raw),
    )
    db.add(record)
    db.flush()
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="ingestion_api_key.created",
            entity_type="workspace_api_key",
            entity_id=record.id,
            event_data={"name": record.name, "prefix": record.prefix},
        )
    )
    db.commit()
    db.refresh(record)
    return ApiKeyCreated(id=record.id, name=record.name, prefix=record.prefix, key=raw)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
) -> None:
    key = db.scalar(
        select(WorkspaceApiKey).where(
            WorkspaceApiKey.id == key_id, WorkspaceApiKey.workspace_id == principal.workspace_id
        )
    )
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    key.revoked_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            event_type="ingestion_api_key.revoked",
            entity_type="workspace_api_key",
            entity_id=key.id,
            event_data={"prefix": key.prefix},
        )
    )
    db.commit()
