FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system voiceevals && useradd --system --gid voiceevals voiceevals
COPY pyproject.toml README.md ./
COPY apps ./apps
COPY workers ./workers
COPY packages ./packages
COPY evals ./evals
RUN pip install --no-cache-dir .
USER voiceevals
CMD ["celery", "-A", "voice_evals_worker.app:celery_app", "worker", "--loglevel=INFO"]
