import os
import sys
from pathlib import Path
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_worker_platform.db")
sys.path.insert(0, str(Path(__file__).parents[2] / "services" / "api"))
sys.path.insert(0, str(Path(__file__).parents[2]))

from sqlalchemy.orm import Session

from app.core.database import make_engine
from app.core.models import Base, Goal, IngestionJob, Resource, ResourceDocument, User
from app.core.storage import put_bytes
from services.worker.worker import process_job


def test_worker_processes_uploaded_document():
    engine = make_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = db.query(User).filter_by(email="worker-test@example.com").first() or User(name="Worker Test", email="worker-test@example.com")
        db.add(user); db.flush()
        goal = Goal(owner_id=user.id, title="Worker test goal"); db.add(goal); db.flush()
        resource = Resource(goal_id=goal.id, title="worker.txt", source_type="file", status="processing"); db.add(resource); db.flush()
        job = IngestionJob(resource_id=resource.id, status="queued", storage_key=f"worker-{uuid.uuid4().hex}.txt"); db.add(job); db.commit()
        put_bytes(job.storage_key, b"worker parsing creates searchable semantic chunks")
        job_id, resource_id, storage_key = str(job.id), str(resource.id), job.storage_key
    process_job({"id": job_id, "kind": "parse_chunk_embed", "payload": {"resource_id": resource_id, "storage_key": storage_key, "filename": "worker.txt"}})
    with Session(engine) as db:
        assert db.get(IngestionJob, uuid.UUID(job_id)).status == "completed"
        assert db.scalar(db.query(ResourceDocument).filter(ResourceDocument.resource_id == uuid.UUID(resource_id)).statement) is not None
