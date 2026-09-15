import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_learning_platform.db")
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def test_student_vertical_slice_and_spatial_preview():
    with TestClient(app) as client:
        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        goal = dashboard.json()["goal"]
        assert "plan_status" in dashboard.json()
        assert dashboard.json()["today"]
        preview = client.post("/api/spatial-context/resolve", json={
            "goal_id": str(goal["id"]),
            "utterance": "Explain this marked step",
            "marks": [{"type": "rectangle", "role": "source", "x": -5, "y": 3, "width": 20, "height": 10}],
        })
        assert preview.status_code == 200
        assert preview.json()["persisted"] is False
        assert preview.json()["resolution"]["normalized_marks"][0]["x"] == 0
        normalized = client.post("/api/spatial-context/resolve", json={
            "goal_id": str(goal["id"]), "utterance": "Explain this marked step",
            "canvas": {"width": 100, "height": 100},
            "marks": [{"type": "rectangle", "role": "reference", "x": 20, "y": 10, "width": 40, "height": 30}],
        })
        assert normalized.status_code == 200
        assert normalized.json()["resolution"]["normalized_marks"][0]["x_norm"] == 0.2
        anchored = client.post("/api/spatial-context/resolve", json={
            "goal_id": str(goal["id"]), "utterance": "Explain this equation", "canvas": {"width": 100, "height": 100},
            "marks": [{"type": "rectangle", "role": "reference", "x": 20, "y": 10, "width": 40, "height": 30}],
            "surface": "pdf", "anchors": [{"id": "eq-1", "type": "equation", "bbox": {"x": 10, "y": 5, "width": 60, "height": 40}}],
        })
        assert anchored.status_code == 200
        assert anchored.json()["resolution"]["resolver"] == "structured-anchor-v1"
        assert anchored.json()["resolution"]["candidates"][0]["anchor_id"] == "eq-1"
        saved = client.post("/api/spatial-context", json={
            "goal_id": str(goal["id"]), "utterance": "Explain this marked step",
            "marks": [{"type": "rectangle", "role": "reference", "x": 20, "y": 10, "width": 40, "height": 30}],
        })
        assert saved.status_code == 200
        assert client.get("/api/operator/analytics").json()["model_health"]["runtime"]["spatial_resolve"]["count"] >= 1
        corrected = client.post(f"/api/spatial-context/{saved.json()['id']}/correct", json={
            "marks": [{"type": "point", "role": "target", "x": 50, "y": 50}],
        })
        assert corrected.status_code == 200
        assert corrected.json()["confidence"] >= 0.99


def test_authentication_and_operator_metadata_boundary():
    with TestClient(app) as client:
        email = "pytest-platform@example.com"
        response = client.post("/api/auth/register", json={"name": "Pytest Student", "email": email, "password": "a-secure-password"})
        if response.status_code == 409:
            response = client.post("/api/auth/login", json={"email": email, "password": "a-secure-password"})
        assert response.status_code == 200
        token = response.json()["access_token"]
        assert client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        profile = client.patch("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
            "education_stage": "3rd_year_college", "graduation_year": 2027,
            "current_skill_level": "intermediate", "known_skills": ["Python", "SQL"],
            "learning_modes": ["practice", "text"], "preferred_pace": "steady",
            "constraints": "college schedule"})
        assert profile.status_code == 200
        assert client.get("/api/me/profile", headers={"Authorization": f"Bearer {token}"}).json()["known_skills"] == ["Python", "SQL"]
        exported = client.get("/api/me/export", headers={"Authorization": f"Bearer {token}"})
        assert exported.status_code == 200
        assert exported.json()["user"]["email"] == email
        assert client.delete("/api/me?confirm=NO", headers={"Authorization": f"Bearer {token}"}).status_code == 400
        assert client.delete("/api/me?confirm=DELETE", headers={"Authorization": f"Bearer {token}"}).json()["status"] == "deleted"
        overview = client.get("/api/operator/overview")
        assert overview.status_code == 200
        assert "private document text" in overview.json()["privacy"]
