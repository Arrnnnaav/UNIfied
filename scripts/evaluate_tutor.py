"""Replayable tutor contract evaluation using an isolated SQLite application instance."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

evaluation_db = Path(__file__).with_name(f"tutor-eval-{uuid.uuid4().hex}.db")
os.environ["DATABASE_URL"] = f"sqlite:///{evaluation_db.as_posix()}"
os.environ["ENVIRONMENT"] = "development"
os.environ["ASYNC_INGESTION"] = "false"
sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "api"))

from fastapi.testclient import TestClient

from app.main import app, engine


def main() -> int:
    try:
        with TestClient(app) as client:
            email = f"eval-{uuid.uuid4().hex}@studyos.local"
            auth = client.post("/api/auth/register", json={"name": "Evaluation Student", "email": email, "password": "evaluation-password"})
            token = auth.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            goal = client.post("/api/goals", headers=headers, json={"title": "Tutor evaluation", "goal_type": "skill", "weekly_hours": 4}).json()
            client.post("/api/resources", headers=headers, json={"title": "HTTP evaluation note", "source_type": "note", "content": "An HTTP response contains a status code, headers, and an optional body."})
            grounded = client.post("/api/tutor/ask", headers=headers, json={"goal_id": goal["id"], "question": "What does an HTTP response contain?"}).json()
            unsupported = client.post("/api/tutor/ask", headers=headers, json={"goal_id": goal["id"], "question": "Explain quantum chromodynamics."}).json()
    finally:
        engine.dispose()
    summary = {"grounded_has_evidence": grounded["evidence_sufficient"], "grounded_has_citation": bool(grounded["citations"]),
               "unsupported_refuses": not unsupported["evidence_sufficient"], "cases": 2}
    print(json.dumps(summary, indent=2))
    return 0 if all(summary[key] for key in ("grounded_has_evidence", "grounded_has_citation", "unsupported_refuses")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
