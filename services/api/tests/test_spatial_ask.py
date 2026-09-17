import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_learning_platform.db")
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.core.providers import resolve_spatial_marks


def _register(client, email):
    response = client.post("/api/auth/register", json={"name": "Spatial Student", "email": email, "password": "a-secure-password"})
    if response.status_code == 409:
        response = client.post("/api/auth/login", json={"email": email, "password": "a-secure-password"})
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_polygon_marks_get_bounding_boxes_and_match_anchors():
    resolution = resolve_spatial_marks(
        [{"type": "polygon", "role": "reference", "points": [[10, 10], [60, 12], [58, 50], [12, 48]]}],
        {"width": 100, "height": 100},
        [{"id": "p-1", "type": "paragraph", "text": "Lorem", "bbox": {"x": 5, "y": 5, "width": 60, "height": 50}}],
    )
    mark = resolution["normalized_marks"][0]
    assert mark["x"] == 10 and mark["y"] == 10 and mark["width"] == 50 and mark["height"] == 40
    assert resolution["candidates"][0]["anchor_id"] == "p-1"
    assert resolution["confidence"] >= 0.9


def test_ask_anywhere_without_goal_persists_page_and_answers_from_anchors():
    with TestClient(app) as client:
        headers = _register(client, "spatial-ask@example.com")
        payload = {
            "question": "What is this?",
            "marks": [{"type": "polygon", "role": "reference", "points": [[100, 100], [300, 100], [300, 200], [100, 200]]}],
            "canvas": {"width": 1280, "height": 720},
            "page": {"url": "https://example.org/anatomy", "title": "Anatomy atlas", "surface": "web"},
            "anchors": [
                {"id": "a1", "type": "img", "text": "Pectoralis major", "bbox": {"x": 90, "y": 90, "width": 220, "height": 120}},
                {"id": "a2", "type": "p", "text": "Unrelated footer", "bbox": {"x": 0, "y": 600, "width": 500, "height": 40}},
            ],
        }
        response = client.post("/api/spatial-context/ask", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"]
        assert "Pectoralis major" in body["answer"]
        assert "Unrelated footer" not in body["answer"]
        assert body["anchors_used"][0]["id"] == "a1"
        assert body["confidence"] > 0
        assert body["page"]["title"] == "Anatomy atlas"

        listed = client.get("/api/spatial-context", headers=headers).json()
        assert listed[0]["id"] == body["id"]
        assert listed[0]["page"]["url"] == "https://example.org/anatomy"
        assert listed[0]["answer"]["text"] == body["answer"]

        follow_up = client.post("/api/spatial-context/ask", json={**payload, "question": "Which nerve supplies it?", "context_id": body["id"]}, headers=headers)
        assert follow_up.status_code == 200
        assert follow_up.json()["id"] == body["id"]
        assert follow_up.json()["turns"] == 2

        other = _register(client, "spatial-other@example.com")
        assert client.get("/api/spatial-context", headers=other) .json() == []
        forbidden = client.post("/api/spatial-context/ask", json={**payload, "context_id": body["id"]}, headers=other)
        assert forbidden.status_code == 404

        exported = client.get("/api/me/export", headers=headers).json()
        assert any(item["id"] == body["id"] for item in exported["spatial_contexts"])


def test_ask_requires_marks_and_rejects_foreign_goal():
    with TestClient(app) as client:
        headers = _register(client, "spatial-ask-2@example.com")
        missing = client.post("/api/spatial-context/ask", json={"question": "Why?", "marks": []}, headers=headers)
        assert missing.status_code == 400
        demo_goal = client.get("/api/dashboard").json()["goal"]
        foreign = client.post("/api/spatial-context/ask", json={"question": "Why?", "goal_id": demo_goal["id"],
                              "marks": [{"type": "point", "x": 1, "y": 1}]}, headers=headers)
        assert foreign.status_code == 404


def test_ask_stream_emits_complete_event():
    with TestClient(app) as client:
        headers = _register(client, "spatial-ask-3@example.com")
        with client.stream("POST", "/api/spatial-context/ask/stream", json={"question": "Explain this", "marks": [{"type": "circle", "x": 10, "y": 10, "width": 30, "height": 30}],
                           "canvas": {"width": 100, "height": 100}}, headers=headers) as response:
            assert response.status_code == 200
            text = "".join(response.iter_text())
        assert "event: complete" in text
