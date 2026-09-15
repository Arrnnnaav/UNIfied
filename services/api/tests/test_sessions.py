import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_learning_sessions.db")
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def test_learning_session_completion_creates_evidence_and_updates_progress():
    with TestClient(app) as client:
        goal = client.get("/api/dashboard").json()["goal"]
        topic = goal["phases"][0]["topics"][0]
        created = client.post("/api/learning-sessions", json={"goal_id": goal["id"], "topic_id": topic["id"], "kind": "practice", "planned_minutes": 30})
        assert created.status_code == 200
        session = created.json()
        assert session["status"] == "planned"
        updated = client.patch(f"/api/learning-sessions/{session['id']}", json={"status": "completed", "actual_minutes": 30, "notes": "Finished recall drill"})
        assert updated.status_code == 200
        assert updated.json()["status"] == "completed"
        assert updated.json()["completed_at"]
        assert client.get("/api/learning-sessions?status=completed").json()
