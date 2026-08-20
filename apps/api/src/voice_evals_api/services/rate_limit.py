from __future__ import annotations

import hashlib
from typing import cast

from fastapi import Depends, HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from ..config import Settings, get_settings
from ..security import Principal, get_principal


def _enforce(
    bucket: str,
    identity: str,
    limit: int,
    window_seconds: int,
    settings: Settings,
) -> None:
    if settings.env.lower() == "test":
        return
    identity_digest = hashlib.sha256(identity.encode()).hexdigest()[:32]
    key = f"voice-evals:rate:{bucket}:{identity_digest}"
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        value = cast(int, redis.incr(key))
        if value == 1:
            redis.expire(key, window_seconds)
        if value > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded; retry after the current window",
                headers={"Retry-After": str(window_seconds)},
            )
    except RedisError as exc:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service is unavailable",
            ) from exc


def login_rate_limit(request: Request, settings: Settings = Depends(get_settings)) -> None:
    client = request.client.host if request.client else "unknown"
    _enforce("login", client, 10, 60, settings)


def ingestion_rate_limit(
    request: Request,
    principal: Principal = Depends(get_principal),
    settings: Settings = Depends(get_settings),
) -> None:
    client = request.client.host if request.client else "unknown"
    _enforce("ingestion", f"{principal.workspace_id}:{client}", 600, 60, settings)
