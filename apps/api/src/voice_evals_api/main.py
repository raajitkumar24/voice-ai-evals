import json
import logging
import secrets
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .bootstrap import bootstrap_local_workspace
from .config import get_settings
from .db import Base, SessionLocal, engine
from .routers import (
    analytics,
    auth,
    datasets,
    eval_runs,
    eval_setup,
    health,
    ingestion,
    providers,
    recommendations,
    regression,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if not settings.is_production:
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_local_workspace(db, settings)
    yield


settings = get_settings()
logger = logging.getLogger("voice_evals_api.requests")
app = FastAPI(
    title="Voice AI Evals API",
    version="0.1.0",
    description="Provider-neutral APIs for Voice AI trace ingestion and evaluation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Token"],
)


@app.middleware("http")
async def request_observability(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            }
        )
    )
    return response


@app.middleware("http")
async def csrf_protection(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if (
        settings.env.lower() != "test"
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path != "/api/v1/auth/login"
        and request.cookies.get("voice_evals_session")
    ):
        cookie_token = request.cookies.get("voice_evals_csrf", "")
        header_token = request.headers.get("X-CSRF-Token", "")
        if not cookie_token or not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(eval_runs.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(regression.router, prefix="/api/v1")
app.include_router(eval_setup.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Voice AI Evals", "docs": "/docs", "health": "/health/ready"}
