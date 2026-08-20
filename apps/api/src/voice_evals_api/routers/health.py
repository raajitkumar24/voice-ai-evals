from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Depends, Response, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    if settings.env.lower() != "test":
        try:
            Redis.from_url(settings.redis_url).ping()
            checks["redis"] = "ok"
        except RedisError:
            checks["redis"] = "unavailable"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if all(value == "ok" for value in checks.values()) else "degraded",
        "checks": checks,
    }


@router.get("/worker")
def worker_health(
    response: Response, settings: Settings = Depends(get_settings)
) -> dict[str, object]:
    try:
        value = cast(
            str | None,
            Redis.from_url(settings.redis_url, decode_responses=True).get(
                "voice-evals:worker-heartbeat"
            ),
        )
        heartbeat = datetime.fromisoformat(value) if value else None
        healthy = bool(heartbeat and (datetime.now(UTC) - heartbeat).total_seconds() <= 90)
    except (RedisError, ValueError):
        heartbeat = None
        healthy = False
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if healthy else "unavailable",
        "last_heartbeat": heartbeat.isoformat() if heartbeat else None,
    }
