#!/bin/sh
set -eu

python -m alembic -c apps/api/alembic.ini upgrade head
exec uvicorn voice_evals_api.main:app --host 0.0.0.0 --port 8000
