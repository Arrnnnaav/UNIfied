import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_learning_platform.db")
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient

from app.main import app, settings

PAYLOAD = {
    "question": "What is this?",
    "marks": [
        {
            "type": "polygon",
            "role": "reference",
            "points": [[100, 100], [300, 100], [300, 200], [100, 200]],
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 100,
        }
    ],
    "canvas": {"width": 1280, "height": 720},
    "page": {
        "url": "https://example.org/anatomy",
        "title": "Anatomy atlas",
        "surface": "web",
    },
    "anchors": [
        {
            "id": "a1",
            "type": "img",
            "text": "Pectoralis major",
            "bbox": {"x": 90, "y": 90, "width": 220, "height": 120},
        }
    ],
    "protocol_version": 2,
    "client_version": "0.2.0",
}


def device_headers():
    return {"X-Device-ID": "dev-" + uuid.uuid4().hex[:12]}


def test_anonymous_device_can_ask_and_sees_quota():
    with TestClient(app) as client:
        headers = device_headers()
        health = client.get("/api/health", headers=headers).json()
        assert health["protocol_version"] == 2 and health["quota"]["signed_in"] is False
        assert health["quota"]["limit"] == settings.spatial_anonymous_daily_limit
        body = client.post(
            "/api/spatial-context/ask", json=PAYLOAD, headers=headers
        ).json()
        assert "Pectoralis major" in body["answer"]
        assert (
            body["quota"]["used"] == 1
            and body["quota"]["remaining"] == settings.spatial_anonymous_daily_limit - 1
        )
        assert (
            body["anchors_used"][0]["role"] == "reference"
            and body["anchors_used"][0]["bbox"]["x"] == 90
        )
        assert body["review_status"] == "pending"
        listed = client.get("/api/spatial-context", headers=headers).json()
        assert listed[0]["id"] == body["id"]
        # another device sees nothing
        assert client.get("/api/spatial-context", headers=device_headers()).json() == []


def test_daily_limit_and_outdated_client(monkeypatch):
    monkeypatch.setattr(settings, "spatial_anonymous_daily_limit", 2)
    with TestClient(app) as client:
        headers = device_headers()
        assert (
            client.post(
                "/api/spatial-context/ask", json=PAYLOAD, headers=headers
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/spatial-context/ask", json=PAYLOAD, headers=headers
            ).status_code
            == 200
        )
        blocked = client.post("/api/spatial-context/ask", json=PAYLOAD, headers=headers)
        assert (
            blocked.status_code == 429
            and blocked.json()["detail"]["code"] == "RATE_LIMITED"
        )
        outdated = client.post(
            "/api/spatial-context/ask",
            json={**PAYLOAD, "protocol_version": 1},
            headers=device_headers(),
        )
        assert (
            outdated.status_code == 426
            and outdated.json()["detail"]["code"] == "CLIENT_OUTDATED"
        )


def test_signup_adopts_device_history_and_quiz_later_creates_review():
    with TestClient(app) as client:
        headers = device_headers()
        first = client.post(
            "/api/spatial-context/ask", json=PAYLOAD, headers=headers
        ).json()
        quiz_anon = client.post(
            f"/api/spatial-context/{first['id']}/quiz", headers=headers
        )
        assert quiz_anon.status_code == 401
        email = f"adopt-{uuid.uuid4().hex[:8]}@example.com"
        registered = client.post(
            "/api/auth/register",
            json={"name": "Adopt", "email": email, "password": "a-secure-password"},
            headers=headers,
        ).json()
        assert registered["adopted_marks"] == 1
        auth = {"Authorization": "Bearer " + registered["access_token"]}
        mine = client.get("/api/spatial-context", headers=auth).json()
        assert [item["id"] for item in mine] == [first["id"]]
        quiz = client.post(f"/api/spatial-context/{first['id']}/quiz", headers=auth)
        assert quiz.status_code == 200 and "Pectoralis major" in quiz.json()["prompt"]
        queue = client.get("/api/review", headers=auth).json()
        assert any(
            item["spatial_context_id"] == first["id"] and item["prompt"]
            for item in queue
        )


def test_stream_emits_status_deltas_and_complete():
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/spatial-context/ask/stream",
            json=PAYLOAD,
            headers=device_headers(),
        ) as response:
            assert response.status_code == 200
            text = "".join(response.iter_text())
        assert (
            "event: status" in text
            and "event: delta" in text
            and "event: complete" in text
        )


def test_operator_review_actions():
    with TestClient(app) as client:
        headers = device_headers()
        body = client.post(
            "/api/spatial-context/ask", json={**PAYLOAD, "anchors": []}, headers=headers
        ).json()
        snapshot = client.get("/api/operator/snapshot").json()
        assert all(
            item["review_status"] == "pending" for item in snapshot["spatial_review"]
        )
        confirmed = client.patch(
            f"/api/operator/spatial/{body['id']}/review", json={"action": "confirm"}
        )
        assert (
            confirmed.status_code == 200
            and confirmed.json()["review_status"] == "confirmed"
            and confirmed.json()["confidence"] >= 0.99
        )
        dismissed = client.patch(
            f"/api/operator/spatial/{body['id']}/review", json={"action": "dismiss"}
        )
        assert dismissed.json()["review_status"] == "dismissed"
        assert (
            client.patch(
                f"/api/operator/spatial/{body['id']}/review", json={"action": "nope"}
            ).status_code
            == 400
        )


def test_audio_endpoints_report_structured_errors():
    with TestClient(app) as client:
        empty = client.post(
            "/api/audio/transcribe",
            files={"audio": ("q.webm", b"", "audio/webm")},
            headers=device_headers(),
        )
        assert (
            empty.status_code == 400 and empty.json()["detail"]["code"] == "EMPTY_AUDIO"
        )
        missing = client.post(
            "/api/audio/synthesize", json={"text": ""}, headers=device_headers()
        )
        assert (
            missing.status_code == 400
            and missing.json()["detail"]["code"] == "EMPTY_TEXT"
        )


def test_burst_limit_and_health_db(monkeypatch):
    monkeypatch.setattr(settings, "spatial_burst_per_minute", 2)
    with TestClient(app) as client:
        headers = device_headers()
        assert client.get("/api/health", headers=headers).json()["db"] == "ok"
        assert client.post("/api/spatial-context/ask", json=PAYLOAD, headers=headers).status_code == 200
        assert client.post("/api/spatial-context/ask", json=PAYLOAD, headers=headers).status_code == 200
        third = client.post("/api/spatial-context/ask", json=PAYLOAD, headers=headers)
        assert third.status_code == 429 and "minute" in third.json()["detail"]["message"]


def test_level_and_client_version_recorded():
    from sqlalchemy import select
    from app.core.models import ModelEvent
    from app.main import engine
    from sqlalchemy.orm import Session
    with TestClient(app) as client:
        body = client.post("/api/spatial-context/ask", json={**PAYLOAD, "level": "eli5", "client_version": "9.9.9"}, headers=device_headers()).json()
        assert body["level"] == "eli5" and body["diagram"] is False
    with Session(engine) as db:
        assert db.scalar(select(ModelEvent).where(ModelEvent.client_version == "9.9.9")) is not None


def test_anonymous_purge_removes_old_device_history():
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.core.models import SpatialContext, User
    from app.main import engine, purge_anonymous
    with TestClient(app) as client:
        headers = device_headers()
        made = client.post("/api/spatial-context/ask", json=PAYLOAD, headers=headers).json()
    with Session(engine) as db:
        context = db.get(SpatialContext, uuid.UUID(made["id"]))
        ghost = db.get(User, context.owner_id)
        old = datetime.utcnow() - timedelta(days=40)
        context.created_at = old; ghost.created_at = old; db.commit()
        assert purge_anonymous(db) >= 1
        assert db.get(SpatialContext, uuid.UUID(made["id"])) is None and db.get(User, ghost.id) is None
