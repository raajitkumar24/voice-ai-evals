from fastapi.testclient import TestClient
from voice_evals_api.main import app


def test_provider_credentials_are_write_only_and_test_provider_is_explicit() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "change-me-before-production"},
        )
        assert login.status_code == 200
        secret = "provider-secret-that-must-not-leak"
        created = client.post(
            "/api/v1/providers",
            json={
                "name": "OpenAI judge",
                "provider": "openai",
                "default_model": "configured-model",
                "api_key": secret,
                "secret_source": "ENCRYPTED_DB",
            },
        )
        assert created.status_code == 201
        assert secret not in created.text
        assert "secret_ciphertext" not in created.text
        listed = client.get("/api/v1/providers")
        assert listed.status_code == 200
        assert secret not in listed.text
        assert "secret_ciphertext" not in listed.text

        test_connection = client.post(
            "/api/v1/providers",
            json={"name": "CI fixture", "provider": "test", "secret_source": "NONE"},
        )
        assert test_connection.status_code == 201
        health = client.post(f"/api/v1/providers/{test_connection.json()['id']}/test")
        assert health.status_code == 200
        assert health.json()["healthy"] is True
