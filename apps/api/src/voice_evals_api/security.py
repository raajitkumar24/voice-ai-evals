from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .db import get_db
from .models import AuthSession, User, WorkspaceApiKey, WorkspaceMembership

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session_token() -> str:
    return secrets.token_urlsafe(48)


def create_api_key() -> tuple[str, str]:
    value = f"ve_{secrets.token_urlsafe(36)}"
    return value, value[:12]


class SecretCipher:
    def __init__(self, key: str | None):
        self._fernet: Fernet | None = None
        if key:
            try:
                raw = base64.urlsafe_b64decode(key)
                if len(raw) != 32:
                    raise ValueError("encryption key must decode to exactly 32 bytes")
                self._fernet = Fernet(base64.urlsafe_b64encode(raw))
            except Exception as exc:
                raise ValueError(
                    "VOICE_EVALS_ENCRYPTION_KEY must be a URL-safe base64 key"
                ) from exc

    @property
    def configured(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if not self._fernet:
            raise RuntimeError("credential encryption is not configured")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not self._fernet:
            raise RuntimeError("credential encryption is not configured")
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("credential cannot be decrypted with the configured key") from exc


@dataclass(frozen=True)
class Principal:
    workspace_id: str
    user_id: str | None
    auth_type: str


def _principal_from_session(db: Session, token: str) -> Principal | None:
    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == digest_token(token),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )
    if not auth_session:
        return None
    return Principal(auth_session.workspace_id, auth_session.user_id, "session")


def _principal_from_api_key(db: Session, token: str) -> Principal | None:
    key = db.scalar(
        select(WorkspaceApiKey).where(
            WorkspaceApiKey.key_hash == digest_token(token), WorkspaceApiKey.revoked_at.is_(None)
        )
    )
    if not key:
        return None
    key.last_used_at = datetime.now(UTC)
    db.commit()
    return Principal(key.workspace_id, None, "api_key")


def get_principal(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias="voice_evals_session"),
    authorization: str | None = Header(default=None),
) -> Principal:
    principal = _principal_from_session(db, session_token) if session_token else None
    if not principal and authorization and authorization.lower().startswith("bearer "):
        principal = _principal_from_api_key(db, authorization[7:].strip())
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return principal


def require_user(principal: Principal = Depends(get_principal)) -> Principal:
    if not principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User session required")
    return principal


def create_db_session(db: Session, user: User, workspace_id: str, settings: Settings) -> str:
    membership = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    raw = create_session_token()
    db.add(
        AuthSession(
            token_hash=digest_token(raw),
            user_id=user.id,
            workspace_id=workspace_id,
            expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    return raw
