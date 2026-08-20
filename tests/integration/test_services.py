import os

import pytest
from redis import Redis
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_postgres_migrations_and_redis_are_reachable() -> None:
    if os.getenv("VOICE_EVALS_RUN_INTEGRATION") != "1":
        pytest.skip("Set VOICE_EVALS_RUN_INTEGRATION=1 with PostgreSQL and Redis URLs")
    database_url = os.environ["VOICE_EVALS_DATABASE_URL"]
    redis_url = os.environ["VOICE_EVALS_REDIS_URL"]
    with create_engine(database_url).connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    assert Redis.from_url(redis_url).ping() is True
