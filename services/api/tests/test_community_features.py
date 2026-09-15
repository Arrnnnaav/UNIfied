import os
import sys
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_community_features.db")
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password, issue_token
from app.core.models import Base, User
from app.main import app, engine, ensure_sqlite_schema


def test_package_identity_monitoring_milestone_and_share_flow():
    suffix = uuid4().hex[:8]
    Base.metadata.create_all(engine)
    ensure_sqlite_schema()
    with Session(engine) as db:
        operator = User(name="Feature Operator", email=f"operator-{suffix}@example.com", password_hash=hash_password("OperatorPass-2026!"), role="operator")
        db.add(operator); db.commit(); db.refresh(operator)
        operator_token = issue_token(str(operator.id), operator.role)
    with TestClient(app) as client:
        student_one = client.post("/api/auth/register", json={"name": "Leader Student", "email": f"leader-{suffix}@example.com", "password": "StudentPass-2026!", "college_name": "Example College", "college_year": "3rd year", "branch": "Computer Science", "college_id": "CS-001"}).json()
        student_two = client.post("/api/auth/register", json={"name": "Member Student", "email": f"member-{suffix}@example.com", "password": "StudentPass-2026!"}).json()
        leader_headers = {"Authorization": f"Bearer {student_one['access_token']}"}
        member_headers = {"Authorization": f"Bearer {student_two['access_token']}"}
        profile = client.get("/api/me/profile", headers=leader_headers).json()
        assert profile["college_name"] == "Example College" and profile["student_id"].startswith("STU-")
        assert client.post("/api/auth/login", json={"email": profile["student_id"], "password": "StudentPass-2026!"}).status_code == 200
        assert client.post("/api/auth/login", json={"email": "CS-001", "password": "StudentPass-2026!"}).status_code == 200
        package = client.post("/api/operator/packages", headers={"Authorization": f"Bearer {operator_token}"}, json={"slug": f"fixed-{suffix}", "title": "Fixed Starter", "status": "published", "manifest": {"phases": [{"title": "Starter", "topics": [{"title": "Foundations", "objectives": ["Explain foundations"], "resources": []}]}], "milestones": [{"title": "First step", "badge_title": "Starter", "criteria": {"type": "sessions", "target": 1}}]}})
        assert package.status_code == 200
        package_id = package.json()["id"]
        installed = client.post(f"/api/packages/{package_id}/install", headers=leader_headers, json={"package_id": package_id})
        assert installed.status_code == 200 and installed.json()["status"] == "installed"
        goal = installed.json()["goal"]
        milestone = client.get("/api/milestones", headers=leader_headers).json()[0]
        dashboard = client.post("/api/operator/monitoring-dashboards", headers={"Authorization": f"Bearer {operator_token}"}, json={"name": "CS Club", "leader_student_id": profile["student_id"]})
        assert dashboard.status_code == 200
        enrolled = client.post(f"/api/operator/monitoring-dashboards/{dashboard.json()['id']}/students", headers={"Authorization": f"Bearer {operator_token}"}, json={"student_id": student_two["user"]["student_id"]})
        assert enrolled.status_code == 200 and enrolled.json()["student_count"] == 1
        shared = client.post(f"/api/milestones/{milestone['id']}/share", headers=leader_headers, json={"recipient_student_id": student_two["user"]["student_id"], "message": "Keep going!"})
        assert shared.status_code == 200
        assert client.get("/api/milestone-shares", headers=member_headers).json()[0]["direction"] == "received"
