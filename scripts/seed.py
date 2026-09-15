"""Create a reproducible operator/student demo dataset without private source text."""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "api"))

from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import get_settings
from app.core.database import make_engine
from app.core.ingestion import chunk_document, content_hash
from app.core.models import Base, Goal, LearningPackage, Phase, Resource, ResourceChunk, ResourceDocument, Topic, User
from app.main import ensure_sqlite_schema


def get_or_create(db: Session, email: str, name: str, role: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(name=name, email=email, role=role, password_hash=hash_password("studyos-demo-2026"))
    db.add(user)
    db.flush()
    return user


def seed_goal(db: Session, user: User, title: str) -> None:
    if db.query(Goal).filter(Goal.owner_id == user.id).first():
        return
    goal = Goal(owner_id=user.id, title=title, goal_type="career", weekly_hours=10)
    db.add(goal)
    db.flush()
    curriculum = {
        "Foundations": ["HTTP and APIs", "SQL and indexing", "Data structures"],
        "Systems": ["Caching", "Authentication", "Deployment"],
        "Proof": ["Build a portfolio service", "Practice technical explanation"],
    }
    for phase_index, (phase_title, topics) in enumerate(curriculum.items()):
        phase = Phase(goal_id=goal.id, title=phase_title, order_index=phase_index)
        db.add(phase)
        db.flush()
        for topic_index, topic_title in enumerate(topics):
            topic = Topic(phase_id=phase.id, title=topic_title, estimated_minutes=35)
            db.add(topic)
            db.flush()
            content = f"This demo source introduces {topic_title}. It explains the core idea, important vocabulary, and gives a short practical example for a student learning {topic_title}."
            resource = Resource(goal_id=goal.id, topic_id=topic.id, title=f"Curated guide: {topic_title}",
                                source_type="operator_curated", trust_status="verified", content=content)
            db.add(resource)
            db.flush()
            document = ResourceDocument(resource_id=resource.id, filename=resource.title, content_hash=content_hash(content),
                                        word_count=len(content.split()), status="processing")
            db.add(document)
            db.flush()
            for item in chunk_document(type("Parsed", (), {"filename": resource.title, "content": content, "pages": (content,)})()):
                db.add(ResourceChunk(document_id=document.id, **item))
            document.status = "ready"


def seed_packages(db: Session, operator: User) -> None:
    catalog = Path(__file__).resolve().parents[1] / "packages" / "catalog"
    for path in sorted(catalog.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if db.query(LearningPackage).filter(LearningPackage.slug == data["slug"], LearningPackage.version == data["version"]).first():
            continue
        db.add(LearningPackage(slug=data["slug"], title=data["title"], description=data.get("description", ""), version=data["version"], status="published", manifest_json=json.dumps(data.get("manifest", {}), ensure_ascii=False), created_by=operator.id, updated_at=__import__("datetime").datetime.utcnow()))


def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    ensure_sqlite_schema()
    with Session(engine) as db:
        operator = get_or_create(db, "operator@studyos.local", "StudyOS Operator", "operator")
        student_a = get_or_create(db, "student-a@studyos.local", "Demo Student A", "student")
        student_b = get_or_create(db, "student-b@studyos.local", "Demo Student B", "student")
        seed_goal(db, student_a, "Become a backend developer")
        seed_goal(db, student_b, "Prepare for technical interviews")
        seed_packages(db, operator)
        db.commit()
        print(f"seeded operator={operator.email} students={student_a.email},{student_b.email}")


if __name__ == "__main__":
    main()
