import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_learning_loop.db")
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def test_learning_loop_connects_resource_tutor_assessment_review_and_operator_metrics():
    with TestClient(app) as client:
        dashboard = client.get("/api/dashboard").json()
        goal = dashboard["goal"]
        topic = goal["phases"][0]["topics"][0]
        new_topic = client.post("/api/topics", json={"phase_id": goal["phases"][0]["id"], "title": "Advanced retrieval", "description": "Follow-on topic", "estimated_minutes": 40})
        assert new_topic.status_code == 200
        dependency = client.post(f"/api/topics/{new_topic.json()['id']}/dependencies", json={"prerequisite_topic_id": topic["id"]})
        assert dependency.status_code == 200

        resource = client.post("/api/resources", json={
            "title": "Retrieval notes",
            "source_type": "note",
            "content": "Semantic retrieval uses embeddings to find meaning-related passages.",
        })
        assert resource.status_code == 200

        tutor = client.post("/api/tutor/ask", json={
            "goal_id": goal["id"], "topic_id": topic["id"], "question": "What does semantic retrieval use?",
        })
        assert tutor.status_code == 200
        assert tutor.json()["evidence_sufficient"] is True
        assert tutor.json()["citations"]
        stream = client.post("/api/tutor/ask/stream", json={
            "goal_id": goal["id"], "question": "What does semantic retrieval use?",
        })
        assert stream.status_code == 200
        assert "event: status" in stream.text and "event: complete" in stream.text

        assessment = client.post(f"/api/topics/{topic['id']}/assessment")
        assert assessment.status_code == 200
        attempt = client.post(f"/api/assessments/{assessment.json()['id']}/attempt", json={
            "answer": "Semantic retrieval uses embeddings to find related passages.",
        })
        assert attempt.status_code == 200
        assert attempt.json()["evidence"] == "assessment_attempt"
        assert client.get("/api/review").status_code == 200

        analytics = client.get("/api/operator/analytics")
        assert analytics.status_code == 200
        assert "assessment" in analytics.json()
        assert "model_health" in analytics.json()
        assert analytics.json()["model_health"]["runtime"]["tutor"]["count"] >= 1
        graph = client.get(f"/api/knowledge-map?goal_id={goal['id']}")
        assert graph.status_code == 200
        assert any(node["type"] == "topic" for node in graph.json()["nodes"])
        assert graph.json()["layers"] == ["curriculum", "semantic", "alignment"]
        assert any(edge["relation"] == "prerequisite_of" for edge in graph.json()["edges"])
        coverage = client.get(f"/api/goals/{goal['id']}/coverage")
        assert coverage.status_code == 200
        assert coverage.json()["method"] == "hybrid-objective-v1"
        concepts = client.get(f"/api/goals/{goal['id']}/semantic-concepts")
        assert concepts.status_code == 200
        assert concepts.json()["concepts"]
        assert concepts.json()["privacy"] == "labels-and-aggregates-only"
        recommendations = client.get(f"/api/goals/{goal['id']}/recommendations")
        assert recommendations.status_code == 200
        assert any(item["topic_id"] == new_topic.json()["id"] and item["dependencies"] for item in recommendations.json())
