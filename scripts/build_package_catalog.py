"""Build fixed, operator-publishable package manifests from Tracker's curated plan.

This is deliberately deterministic: no LLM is called and the source plan remains
the authoring authority. The generated JSON can be uploaded through the operator
package endpoint or seeded into a deployment.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKER_PLAN = Path(r"D:\tracker\arnav-learning-plan.json")
OUT = ROOT / "packages" / "catalog"


def build_package(plan: dict, phase_id: str, slug: str, title: str) -> dict:
    links = {str(item.get("id")): item for item in plan.get("links", [])}
    phase = next(item for item in plan.get("phases", []) if item.get("id") == phase_id)
    topics = []
    for index, step in enumerate(phase.get("steps", [])):
        resource = links.get(str(step.get("resource"))) if step.get("resource") else None
        action = str(step.get("action", step.get("title", f"Study step {index + 1}")))
        topic = {"key": f"{phase_id}-{index + 1}", "title": action[:200], "description": action[:1500],
                 "difficulty": "advanced" if any(word in action.lower() for word in ("build", "production", "paper")) else "intermediate",
                 "estimated_minutes": 45, "objectives": ["Explain the central idea", "Apply it in a small exercise", "Record evidence of understanding"], "resources": []}
        if resource:
            topic["resources"].append({"title": resource.get("title", resource.get("id", "Curated resource")), "url": resource.get("url"), "source_type": resource.get("category", "curated")[:30], "content": resource.get("description", "")})
        topics.append(topic)
    return {"slug": slug, "title": title, "description": f"Fixed operator-curated pathway from Tracker's {phase.get('name', title)} plan. No per-student curriculum generation.", "version": "1.0.0", "status": "published", "manifest": {"goal_type": "skill", "weekly_hours": 8, "learning_flow": ["Learn the concept", "Read the curated material", "Watch an associated video when present", "Build or practice", "Complete recall and review"], "source": "tracker-curated-v1", "phases": [{"title": phase.get("name", title), "topics": topics}], "milestones": [{"title": f"Complete {title} foundations", "description": "Finish the fixed pathway and produce evidence through sessions and assessments.", "badge_title": f"{title} Foundations", "criteria": {"type": "progress", "progress": 1, "target": max(1, min(8, len(topics) // 3))}}]}}


def main() -> None:
    if not TRACKER_PLAN.exists():
        raise SystemExit(f"Tracker plan not found: {TRACKER_PLAN}")
    plan = json.loads(TRACKER_PLAN.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    selections = [("rag", "rag-mastery", "RAG Mastery"), ("agents", "agent-foundations", "Agent Foundations"), ("localllm", "local-llm", "Local & On-Prem LLMs"), ("multimodal", "multimodal-rag", "Multimodal RAG")]
    for phase_id, slug, title in selections:
        target = OUT / f"{slug}.json"
        target.write_text(json.dumps(build_package(plan, phase_id, slug, title), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(target)


if __name__ == "__main__":
    main()
