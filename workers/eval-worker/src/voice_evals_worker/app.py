from celery import Celery
from celery.signals import heartbeat_sent, worker_ready
from redis import Redis
from voice_evals_api.config import get_settings

settings = get_settings()
celery_app = Celery("voice-ai-evals", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    task_always_eager=settings.env.lower() in {"test", "demo"},
    task_eager_propagates=True,
)

celery_app.autodiscover_tasks(["voice_evals_worker"])


def _record_heartbeat() -> None:
    from datetime import UTC, datetime

    Redis.from_url(settings.redis_url, decode_responses=True).set(
        "voice-evals:worker-heartbeat", datetime.now(UTC).isoformat(), ex=120
    )


@worker_ready.connect  # type: ignore[untyped-decorator]
def on_worker_ready(**_: object) -> None:
    _record_heartbeat()


@heartbeat_sent.connect  # type: ignore[untyped-decorator]
def on_worker_heartbeat(**_: object) -> None:
    _record_heartbeat()


@celery_app.task(name="voice_evals.health")  # type: ignore[untyped-decorator]
def health() -> dict[str, str]:
    return {"status": "ok"}
