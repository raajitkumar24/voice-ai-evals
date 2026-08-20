# Deployment and Operations

## Services

The supported deployment contains the Next.js web service, FastAPI API, Celery worker, PostgreSQL, and Redis. Docker Compose is the reference local/self-hosted topology; production orchestrators may map the same process boundaries.

## Required configuration

Set `VOICE_EVALS_DATABASE_URL`, `VOICE_EVALS_REDIS_URL`, `VOICE_EVALS_BOOTSTRAP_EMAIL`, a non-default `VOICE_EVALS_BOOTSTRAP_PASSWORD`, `VOICE_EVALS_ENCRYPTION_KEY`, and the exact CORS origin list. Provider keys may be supplied per workspace through encrypted storage or through server environment variables.

## Health and observability

- `/health/live`: API process liveness
- `/health/ready`: PostgreSQL and Redis readiness
- `/health/worker`: last Celery worker heartbeat

API responses include `X-Request-ID`. Structured request logs contain method, path, status, and duration—not transcripts, knowledge content, credentials, or request bodies. Eval runs persist provider/model provenance, fallback/retry metadata, token usage, latency, and normalized errors.

## Backups and recovery

Back up PostgreSQL and the deployment encryption key separately. Redis is a queue/result transport and should use persistence appropriate to the installation, but PostgreSQL remains authoritative. Test database restores and credential decryption in a protected staging environment.

## Scaling

Scale API and web services horizontally. Scale Celery workers based on provider quotas and job latency; keep prefetch at one for fair long-running eval work. Redis-backed request limits and per-run call ceilings protect shared installations.

## Upgrades

Back up the database, deploy one release across API/worker/web, run `alembic upgrade head`, then verify all health endpoints. Alembic revisions include downgrades, but data backups are the primary rollback mechanism.
