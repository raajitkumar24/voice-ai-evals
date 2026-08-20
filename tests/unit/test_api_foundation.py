from fastapi.testclient import TestClient
from voice_evals_api.main import app


def test_health_and_openapi_are_available() -> None:
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["checks"]["database"] == "ok"
        assert client.get("/openapi.json").status_code == 200


def test_local_login_cookie_and_api_key_one_time_response() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "change-me-before-production"},
        )
        assert login.status_code == 200
        cookie = login.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "change-me-before-production" not in login.text

        created = client.post("/api/v1/auth/api-keys", json={"name": "test-ingestion"})
        assert created.status_code == 201
        issued_key = created.json()["key"]
        assert issued_key.startswith("ve_")
        assert issued_key not in client.get("/api/v1/auth/me").text
