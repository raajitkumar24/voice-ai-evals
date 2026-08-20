from fastapi.testclient import TestClient
from voice_evals_api.db import SessionLocal
from voice_evals_api.main import app
from voice_evals_api.models import ProviderConnection, Workspace


def test_provider_connections_cannot_cross_workspace_boundary() -> None:
    with TestClient(app) as client:
        with SessionLocal() as db:
            other_workspace = Workspace(
                name="Other Workspace", slug="other-isolation-workspace"
            )
            db.add(other_workspace)
            db.flush()
            foreign_connection = ProviderConnection(
                workspace_id=other_workspace.id,
                name="Foreign provider",
                provider="test",
                secret_source="NONE",
            )
            db.add(foreign_connection)
            db.commit()
            foreign_id = foreign_connection.id
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.com", "password": "change-me-before-production"},
            ).status_code
            == 200
        )
        visible = client.get("/api/v1/providers")
        assert visible.status_code == 200
        assert foreign_id not in {item["id"] for item in visible.json()}
        assert client.post(f"/api/v1/providers/{foreign_id}/test").status_code == 404
