import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from fastapi.testclient import TestClient

from app.main import app


def test_me_reports_onboarding_state_and_role():
    with TestClient(app) as client:
        email = f"me-{uuid.uuid4().hex[:8]}@example.com"
        registered = client.post(
            "/api/auth/register",
            json={"name": "Me", "email": email, "password": "a-secure-password"},
        ).json()
        auth = {"Authorization": "Bearer " + registered["access_token"]}
        me = client.get("/api/auth/me", headers=auth).json()
        assert (
            me["email"] == email
            and me["role"] == "student"
            and me["has_goals"] is False
            and me["profile_complete"] is False
        )
        client.patch(
            "/api/me/profile", json={"education_stage": "undergraduate"}, headers=auth
        )
        client.post("/api/goals", json={"title": "Learn linear algebra"}, headers=auth)
        me = client.get("/api/auth/me", headers=auth).json()
        assert (
            me["has_goals"] is True
            and me["profile_complete"] is True
            and me["student_id"]
        )


def test_me_rejects_bad_token():
    with TestClient(app) as client:
        assert (
            client.get(
                "/api/auth/me", headers={"Authorization": "Bearer nope"}
            ).status_code
            == 401
        )


def test_cors_allows_configured_web_origin(monkeypatch):
    from app.main import settings

    assert "http://localhost:5173" in settings.web_origins
