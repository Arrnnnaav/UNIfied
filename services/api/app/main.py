from __future__ import annotations

import json
import re
import threading
import uuid
import io
import zipfile
from collections import defaultdict
from time import perf_counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db, make_engine
from app.core.models import Assessment, AssessmentAttempt, AuditLog, Base, Goal, IngestionJob, LearnerProfile, LearningObjective, LearningPackage, LearningSession, MasteryEvidence, Milestone, MilestoneShare, ModelEvent, MonitoringDashboard, MonitoringMember, PackageInstall, Phase, Resource, ResourceChunk, ResourceDocument, ReviewItem, SemanticConcept, SpatialContext, SpatialCorrection, Topic, TopicConceptAlignment, TopicDependency, User
from app.core.jobs import enqueue_optional
from app.core.llm import grounded_completion
from app.core.storage import put_bytes
from app.core.web_ingestion import fetch_github_text, fetch_web_text, fetch_youtube_transcript
from app.core.ingestion import chunk_document, content_hash, parse_document
from app.core.auth import decode_token, hash_password, issue_token, verify_password
from app.core.providers import choose_model, cosine_similarity, embed_text, resolve_spatial_marks, warm_local_models
from app.core.schemas import AssessmentAttemptCreate, DependencyCreate, GoalCreate, LearnerProfileUpdate, LearningSessionCreate, LearningSessionUpdate, LoginRequest, MilestoneCreate, MilestoneShareCreate, MonitoringDashboardCreate, MonitoringMemberCreate, ObjectiveCreate, PackageCreate, PackageInstallCreate, ProgressUpdate, RegisterRequest, ResourceCreate, SpatialContextCreate, SpatialCorrectionCreate, TopicCreate, TopicUpdate, TutorAsk

settings = get_settings()
engine = make_engine(settings.database_url)
warmup_status = {"status": "not-run"}


def schedule_model_warmup() -> None:
    global warmup_status
    if not settings.local_llm_base_url:
        warmup_status = {"status": "not-configured"}
        return
    warmup_status = {"status": "scheduled", "provider": "local", "model": settings.local_llm_model}
    def run() -> None:
        global warmup_status
        warmup_status = warm_local_models()
    threading.Thread(target=run, name="studyos-model-warmup", daemon=True).start()


def current_user(db: Session, request: Request | None = None) -> User:
    authorization = request.headers.get("Authorization", "") if request else ""
    if authorization.lower().startswith("bearer "):
        try:
            claims = decode_token(authorization.split(" ", 1)[1])
            user = db.get(User, parse_id(claims["sub"]))
            if user:
                return user
        except Exception as exc:
            raise HTTPException(401, "invalid or expired token") from exc
    if settings.environment != "development":
        raise HTTPException(401, "authentication required")
    user = db.scalar(select(User).where(User.email == "demo@student.local"))
    if not user:
        user = User(name="Demo Student", email="demo@student.local", role="student")
        db.add(user); db.commit(); db.refresh(user)
    return user


def parse_id(value: str) -> uuid.UUID:
    try: return uuid.UUID(value)
    except ValueError as exc: raise HTTPException(400, "invalid id") from exc


def audit(db: Session, actor: User, action: str, entity_type: str, entity_id: str, before: dict, after: dict) -> None:
    db.add(AuditLog(actor_id=actor.id, action=action, entity_type=entity_type, entity_id=entity_id,
                    before_json=json.dumps(before), after_json=json.dumps(after)))


def percentile(values: list[int], ratio: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * ratio)))]


def hybrid_chunk_score(query: str, query_vector: list[float], chunk: ResourceChunk) -> float:
    vector_score = cosine_similarity(query_vector, json.loads(chunk.embedding_json or "[]")) if chunk.embedding_json not in {"", "[]"} else 0.0
    query_terms = {term for term in re.findall(r"[a-z0-9_]+", query.lower()) if len(term) > 2}
    chunk_terms = set(re.findall(r"[a-z0-9_]+", chunk.text.lower()))
    lexical_ratio = len(query_terms & chunk_terms) / len(query_terms) if query_terms else 0.0
    return max(vector_score, min(0.95, 0.10 + lexical_ratio * 0.55)) if lexical_ratio else vector_score


SEMANTIC_STOPWORDS = {"this", "that", "with", "from", "into", "have", "has", "will", "your", "their", "about", "then", "than", "what", "when", "where", "which", "also", "only", "using", "uses", "used", "the", "and", "for", "are", "was", "were", "not", "but", "one", "short", "core"}


def semantic_terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z][a-z0-9_-]{3,}", text.lower()) if term not in SEMANTIC_STOPWORDS]


def plan_status(goal: Goal, topics: list[Topic]) -> dict:
    remaining_minutes = sum(round(topic.estimated_minutes * max(0.15, 1 - topic.progress)) for topic in topics if topic.mastery < .8 or topic.progress < 1)
    if not goal.target_date:
        return {"label": "Insufficient data", "reason": "Add a target date to compare remaining work with available capacity.", "remaining_minutes": remaining_minutes, "available_minutes": None}
    days = max(1, (goal.target_date - datetime.utcnow().date()).days)
    available_minutes = round(goal.weekly_hours * 60 * days / 7)
    ratio = remaining_minutes / max(available_minutes, 1)
    if ratio <= .75:
        label, reason = "Ahead", "Your remaining estimated work fits comfortably inside available weekly capacity."
    elif ratio <= 1:
        label, reason = "On track", "Your remaining estimated work fits inside available capacity if study sessions stay consistent."
    elif ratio <= 1.25:
        label, reason = "At risk", "Remaining work is close to or above available capacity; prioritize prerequisite gaps."
    else:
        label, reason = "Behind", "Remaining work exceeds available capacity; reduce scope or increase weekly study time."
    return {"label": label, "reason": reason, "remaining_minutes": remaining_minutes, "available_minutes": available_minutes, "days_remaining": days}


def synthesis_route_configured() -> bool:
    return bool(settings.local_llm_base_url or settings.openai_api_key or settings.anthropic_api_key)


def synthesis_route_ready() -> bool:
    if settings.local_llm_base_url:
        try:
            import httpx
            with httpx.Client(trust_env=False, timeout=0.75) as client:
                response = client.get(f"{settings.local_llm_base_url.rstrip('/')}/models")
            return response.is_success
        except Exception:
            return False
    return bool(settings.openai_api_key or settings.anthropic_api_key)


def record_model_event(db: Session, task: str, metadata: dict, latency_ms: int, confidence: float | None = None) -> None:
    """Persist aggregate-safe model telemetry; prompts, answers, and document text never enter this record."""
    db.add(ModelEvent(task=task, provider=str(metadata.get("provider", "unknown")),
                      model=str(metadata.get("model", "unknown")), status=str(metadata.get("status", "unknown")),
                      latency_ms=max(0, int(latency_ms)), confidence=confidence))


def serialize_topic(topic: Topic) -> dict:
    return {"id": str(topic.id), "title": topic.title, "description": topic.description,
            "difficulty": topic.difficulty, "estimated_minutes": topic.estimated_minutes, "progress": topic.progress,
            "mastery": topic.mastery, "phase_id": str(topic.phase_id),
            "resource_count": len(topic.resources)}


def serialize_goal(goal: Goal) -> dict:
    phases = []
    for phase in sorted(goal.phases, key=lambda p: p.order_index):
        phases.append({"id": str(phase.id), "title": phase.title, "order_index": phase.order_index,
                       "topics": [serialize_topic(t) for t in phase.topics]})
    return {"id": str(goal.id), "title": goal.title, "goal_type": goal.goal_type,
            "target_date": str(goal.target_date) if goal.target_date else None,
            "weekly_hours": goal.weekly_hours, "status": goal.status, "phases": phases,
            "resource_count": len(goal.resources)}


def seed_demo(db: Session, user: User) -> None:
    if db.scalar(select(Goal).where(Goal.owner_id == user.id)): return
    goal = Goal(owner_id=user.id, title="Build strong foundations for an AI/ML engineering career",
                goal_type="career", weekly_hours=10)
    db.add(goal); db.flush()
    seeds = [("RAG & Retrieval", ["Embeddings and semantic search", "Hybrid BM25 + vector search", "RAG evaluation"]),
             ("Agents & Systems", ["Tool use and ReAct", "Agent memory", "Production FastAPI services"]),
             ("Build & Prove", ["Ship a portfolio project", "Write technical case studies"])]
    for pi, (title, topics) in enumerate(seeds):
        phase = Phase(goal_id=goal.id, title=title, order_index=pi); db.add(phase); db.flush()
        for ti, topic in enumerate(topics):
            topic_record = Topic(phase_id=phase.id, title=topic, description="A measurable learning unit with evidence, not just a bookmark.",
                                 estimated_minutes=35 + ti * 10)
            db.add(topic_record); db.flush()
            db.add(LearningObjective(topic_id=topic_record.id, text=f"explain {topic.lower()}", order_index=0))
    db.add(Resource(goal_id=goal.id, title="Your learning plan", source_type="imported",
                    content="Use your saved resources as evidence. Completion is not mastery."))
    db.commit()


def ensure_sqlite_schema() -> None:
    """Tiny dev bridge until Alembic migrations are added; production runs migrations before startup."""
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    with engine.begin() as connection:
        migrations = {
            "spatial_contexts": {
                "sensitivity_class": "VARCHAR(30) DEFAULT 'private'", "confidence": "FLOAT DEFAULT 0",
                "resolution_json": "TEXT DEFAULT '{}'", "processing_ms": "INTEGER DEFAULT 0",
            },
            "users": {"password_hash": "VARCHAR(255) DEFAULT ''", "role": "VARCHAR(30) DEFAULT 'student'", "student_id": "VARCHAR(30)"},
            "learner_profiles": {"college_name": "VARCHAR(200) DEFAULT ''", "college_year": "VARCHAR(40) DEFAULT ''", "branch": "VARCHAR(120) DEFAULT ''", "college_id": "VARCHAR(120) DEFAULT ''", "coding_profiles_json": "TEXT DEFAULT '{}'"},
            "ingestion_jobs": {"storage_key": "VARCHAR(500) DEFAULT ''"},
            "resource_chunks": {"embedding_json": "TEXT DEFAULT '[]'", "embedding": "TEXT DEFAULT NULL"},
            "resources": {"trust_status": "VARCHAR(30) DEFAULT 'unverified'", "updated_at": "DATETIME"},
            "audit_logs": {},
            "learning_objectives": {},
        }
        for table, columns in migrations.items():
            if table not in inspector.get_table_names():
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        if "users" in inspector.get_table_names():
            rows = connection.execute(text("SELECT id FROM users WHERE student_id IS NULL OR student_id = ''")).fetchall()
            for row in rows:
                connection.execute(text("UPDATE users SET student_id=:student_id WHERE id=:id"), {"student_id": f"STU-{uuid.uuid4().hex[:10].upper()}", "id": row[0]})


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "development" and settings.jwt_secret_key == "change-me-in-production-please":
        raise RuntimeError("JWT_SECRET_KEY must be replaced before production startup")
    if settings.environment != "development" and not synthesis_route_configured():
        raise RuntimeError("Configure LOCAL_LLM_BASE_URL, OPENAI_API_KEY, or ANTHROPIC_API_KEY before production startup")
    if settings.environment == "development":
        Base.metadata.create_all(engine)
        ensure_sqlite_schema()
        with Session(engine) as db:
            seed_demo(db, current_user(db))
    schedule_model_warmup()
    yield


app = FastAPI(title="Unified Learning Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/api/health")
def health(): return {"status": "ok", "product": "Unified Learning Platform"}


@app.get("/api/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/api/health/ready")
def readiness(response: Response):
    checks = {"database": False, "queue": False, "model_route": synthesis_route_ready()}
    try:
        with engine.connect() as connection: connection.exec_driver_sql("SELECT 1")
        checks["database"] = True
    except Exception:
        pass
    try:
        import redis
        redis.from_url(settings.redis_url, socket_connect_timeout=.25).ping()
        checks["queue"] = True
    except Exception:
        pass
    healthy = all(checks.values()) or settings.environment == "development"
    if not healthy:
        response.status_code = 503
    return {"status": "ok" if healthy else "degraded", "checks": checks, "warmup": warmup_status,
            "model_routes": {task: choose_model(task, task == "spatial_resolve").__dict__ for task in ["spatial_resolve", "tutor", "assessment", "recommendation"]}}


@app.post("/api/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "email already registered")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="student")
    db.add(user); db.flush()
    db.add(LearnerProfile(user_id=user.id, college_name=payload.college_name.strip(), college_year=payload.college_year.strip(), branch=payload.branch.strip(), college_id=payload.college_id.strip()))
    db.commit(); db.refresh(user)
    return {"access_token": issue_token(str(user.id), user.role), "token_type": "bearer",
            "user": {"id": str(user.id), "student_id": user.student_id, "name": user.name, "role": user.role}}


def serialize_profile(profile: LearnerProfile) -> dict:
    return {"id": str(profile.id), "education_stage": profile.education_stage, "graduation_year": profile.graduation_year,
            "current_skill_level": profile.current_skill_level, "known_skills": json.loads(profile.known_skills_json or "[]"),
            "learning_modes": json.loads(profile.learning_modes_json or "[\"mixed\"]"), "preferred_pace": profile.preferred_pace,
            "constraints": profile.constraints, "college_name": profile.college_name, "college_year": profile.college_year,
            "branch": profile.branch, "college_id": profile.college_id,
            "coding_profiles": json.loads(profile.coding_profiles_json or "{}")}


def serialize_package(package: LearningPackage, include_manifest: bool = False) -> dict:
    data = {"id": str(package.id), "slug": package.slug, "title": package.title, "description": package.description,
            "version": package.version, "status": package.status, "created_at": package.created_at.isoformat(),
            "updated_at": package.updated_at.isoformat()}
    if include_manifest:
        data["manifest"] = json.loads(package.manifest_json or "{}")
    return data


def package_manifest(value: dict) -> dict:
    manifest = value if isinstance(value, dict) else {}
    phases = manifest.get("phases", [])
    if not isinstance(phases, list) or len(phases) > 100:
        raise HTTPException(422, "package phases must be a list of at most 100 items")
    for phase in phases:
        if not isinstance(phase, dict) or not str(phase.get("title", "")).strip():
            raise HTTPException(422, "each package phase needs a title")
        if not isinstance(phase.get("topics", []), list):
            raise HTTPException(422, "phase topics must be a list")
    if len(json.dumps(manifest, ensure_ascii=False)) > 5_000_000:
        raise HTTPException(413, "package manifest exceeds 5 MB")
    return manifest


def serialize_milestone(item: Milestone) -> dict:
    return {"id": str(item.id), "goal_id": str(item.goal_id), "title": item.title, "description": item.description,
            "badge_title": item.badge_title, "target_date": str(item.target_date) if item.target_date else None,
            "criteria": json.loads(item.criteria_json or "{}"), "progress": round(item.progress, 3), "status": item.status,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None}


@app.get("/api/me/profile")
def get_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile:
        profile = LearnerProfile(user_id=user.id)
        db.add(profile); db.commit(); db.refresh(profile)
    data = serialize_profile(profile); data["student_id"] = user.student_id; data["name"] = user.name; data["email"] = user.email
    return data


@app.patch("/api/me/profile")
def update_profile(payload: LearnerProfileUpdate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile:
        profile = LearnerProfile(user_id=user.id)
        db.add(profile)
    profile.education_stage = payload.education_stage.strip() or "other"
    profile.graduation_year = payload.graduation_year
    profile.current_skill_level = payload.current_skill_level.strip() or "beginner"
    profile.known_skills_json = json.dumps([item.strip()[:100] for item in payload.known_skills if item.strip()][:50])
    profile.learning_modes_json = json.dumps([item.strip()[:40] for item in payload.learning_modes if item.strip()][:10] or ["mixed"])
    profile.preferred_pace = payload.preferred_pace.strip() or "steady"
    profile.constraints = payload.constraints.strip()
    profile.college_name = payload.college_name.strip()
    profile.college_year = payload.college_year.strip()
    profile.branch = payload.branch.strip()
    profile.college_id = payload.college_id.strip()
    profile.coding_profiles_json = json.dumps({str(key)[:40]: str(value)[:300] for key, value in payload.coding_profiles.items() if str(value).strip()})
    profile.updated_at = datetime.utcnow()
    db.commit(); db.refresh(profile)
    data = serialize_profile(profile); data["student_id"] = user.student_id; data["name"] = user.name; data["email"] = user.email
    return data


def require_operator(request: Request, db: Session) -> User:
    actor = current_user(db, request)
    if actor.role != "operator":
        raise HTTPException(403, "operator role required")
    return actor


@app.get("/api/packages")
def available_packages(request: Request, db: Session = Depends(get_db)):
    current_user(db, request)
    packages = db.scalars(select(LearningPackage).where(LearningPackage.status == "published").order_by(LearningPackage.title)).all()
    return [serialize_package(item) for item in packages]


@app.get("/api/packages/{package_id}/download")
def download_package(package_id: str, request: Request, db: Session = Depends(get_db)):
    current_user(db, request)
    package = db.get(LearningPackage, parse_id(package_id))
    if not package or package.status != "published": raise HTTPException(404, "package not found")
    return {"filename": f"{package.slug}-{package.version}.json", **serialize_package(package, include_manifest=True)}


@app.post("/api/packages/{package_id}/install")
def install_package(package_id: str, payload: PackageInstallCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); package = db.get(LearningPackage, parse_id(package_id))
    if not package or package.status != "published": raise HTTPException(404, "package not found")
    existing = db.scalar(select(PackageInstall).where(PackageInstall.user_id == user.id, PackageInstall.package_id == package.id))
    if existing: return {"package": serialize_package(package), "goal": serialize_goal(db.get(Goal, existing.goal_id)), "status": "already_installed"}
    manifest = json.loads(package.manifest_json or "{}")
    goal = Goal(owner_id=user.id, title=(payload.goal_title or package.title)[:200], goal_type=manifest.get("goal_type", "skill"), weekly_hours=int(manifest.get("weekly_hours", 8)))
    db.add(goal); db.flush()
    topic_by_key = {}
    for phase_index, phase_data in enumerate(manifest.get("phases", [])):
        phase = Phase(goal_id=goal.id, title=str(phase_data["title"])[:200], order_index=phase_index); db.add(phase); db.flush()
        for topic_index, topic_data in enumerate(phase_data.get("topics", [])):
            topic = Topic(phase_id=phase.id, title=str(topic_data.get("title", "Untitled topic"))[:200], description=str(topic_data.get("description", ""))[:2000], difficulty=str(topic_data.get("difficulty", "intermediate"))[:30], estimated_minutes=max(5, min(600, int(topic_data.get("estimated_minutes", 30)))))
            db.add(topic); db.flush(); topic_by_key[topic_data.get("key", topic.title)] = topic
            for objective_index, objective_text in enumerate(topic_data.get("objectives", [])):
                db.add(LearningObjective(topic_id=topic.id, text=str(objective_text)[:500], order_index=objective_index))
            for resource_data in topic_data.get("resources", []):
                resource_content = str(resource_data.get("content", ""))[:1_000_000]
                resource = Resource(goal_id=goal.id, topic_id=topic.id, title=str(resource_data.get("title", "Package resource"))[:240], url=resource_data.get("url"), source_type=str(resource_data.get("source_type", "package"))[:30], content=resource_content, status="ready" if resource_content else "pending", trust_status="verified")
                db.add(resource); db.flush()
                if resource_content:
                    document = ResourceDocument(resource_id=resource.id, filename=resource.title[:255], content_hash=content_hash(resource_content), word_count=len(resource_content.split()), status="processing")
                    db.add(document); db.flush()
                    for chunk_data in chunk_document(type("Parsed", (), {"filename": resource.title, "content": resource_content, "pages": (resource_content,)})()): db.add(ResourceChunk(document_id=document.id, **chunk_data))
                    document.status = "ready"
    for milestone_data in manifest.get("milestones", []):
        db.add(Milestone(goal_id=goal.id, title=str(milestone_data.get("title", "Milestone"))[:200], description=str(milestone_data.get("description", ""))[:1000], badge_title=str(milestone_data.get("badge_title", ""))[:120], criteria_json=json.dumps(milestone_data.get("criteria", {}))))
    db.add(PackageInstall(user_id=user.id, package_id=package.id, goal_id=goal.id)); db.commit(); db.refresh(goal)
    return {"package": serialize_package(package), "goal": serialize_goal(goal), "status": "installed"}


@app.get("/api/operator/packages")
def operator_packages(request: Request, db: Session = Depends(get_db)):
    require_operator(request, db)
    return [serialize_package(item) for item in db.scalars(select(LearningPackage).order_by(LearningPackage.updated_at.desc())).all()]


@app.post("/api/operator/packages")
def create_operator_package(payload: PackageCreate, request: Request, db: Session = Depends(get_db)):
    actor = require_operator(request, db)
    if payload.status not in {"draft", "published", "archived"}: raise HTTPException(400, "invalid package status")
    manifest = package_manifest(payload.manifest)
    package = LearningPackage(slug=payload.slug, title=payload.title.strip(), description=payload.description.strip(), version=payload.version, status=payload.status, manifest_json=json.dumps(manifest, ensure_ascii=False), created_by=actor.id, updated_at=datetime.utcnow())
    db.add(package); db.flush(); audit(db, actor, "package.created", "learning_package", str(package.id), {}, {"slug": package.slug, "version": package.version, "status": package.status}); db.commit(); db.refresh(package)
    return serialize_package(package, include_manifest=True)


@app.post("/api/operator/packages/upload")
async def upload_operator_package(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    actor = require_operator(request, db); raw = await file.read()
    try:
        if file.filename and file.filename.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = [name for name in archive.namelist() if name.lower().endswith("manifest.json")]
                if not names: raise ValueError("ZIP must contain manifest.json")
                data = json.loads(archive.read(names[0]).decode("utf-8"))
        else: data = json.loads(raw.decode("utf-8"))
        payload = PackageCreate.model_validate(data)
    except Exception as exc:
        raise HTTPException(422, f"invalid package manifest: {str(exc)[:200]}") from exc
    return create_operator_package(payload, request, db)


@app.patch("/api/operator/packages/{package_id}/status")
def publish_operator_package(package_id: str, request: Request, status: str = Query(...), db: Session = Depends(get_db)):
    actor = require_operator(request, db)
    if status not in {"draft", "published", "archived"}: raise HTTPException(400, "invalid package status")
    package = db.get(LearningPackage, parse_id(package_id))
    if not package: raise HTTPException(404, "package not found")
    before = {"status": package.status}; package.status = status; package.updated_at = datetime.utcnow(); audit(db, actor, "package.status_changed", "learning_package", str(package.id), before, {"status": status}); db.commit(); db.refresh(package)
    return serialize_package(package)


def monitoring_summary(user: User, db: Session) -> dict:
    goals = db.scalars(select(Goal).where(Goal.owner_id == user.id)).all()
    topics = [topic for goal in goals for phase in goal.phases for topic in phase.topics]
    sessions = db.scalars(select(LearningSession).where(LearningSession.goal_id.in_([goal.id for goal in goals]))).all() if goals else []
    completed = [item for item in sessions if item.status == "completed"]
    last_activity = max((item.completed_at or item.created_at for item in sessions), default=None)
    cutoff = datetime.utcnow() - timedelta(days=30)
    active_days = len({(item.completed_at or item.created_at).date() for item in completed if (item.completed_at or item.created_at) >= cutoff})
    recent_sessions = sum((item.completed_at or item.created_at) >= datetime.utcnow() - timedelta(days=14) for item in completed)
    return {"student_id": user.student_id, "name": user.name, "college": (user.profile.college_name if user.profile else ""),
            "year": (user.profile.college_year if user.profile else ""), "branch": (user.profile.branch if user.profile else ""), "goals": len(goals), "topics": len(topics),
            "average_progress": round(sum(topic.progress for topic in topics) / len(topics), 3) if topics else 0,
            "average_mastery": round(sum(topic.mastery for topic in topics) / len(topics), 3) if topics else 0,
            "completed_sessions": len(completed), "session_minutes": sum(item.actual_minutes for item in completed),
            "active_days_30": active_days, "sessions_last_14_days": recent_sessions,
            "last_activity": last_activity.isoformat() if last_activity else None,
            "on_track": any(plan_status(goal, [topic for phase in goal.phases for topic in phase.topics])["label"] in {"Ahead", "On track"} for goal in goals) if goals else False}


def serialize_monitoring_dashboard(dashboard: MonitoringDashboard, db: Session) -> dict:
    leader = db.get(User, dashboard.leader_user_id)
    members = db.scalars(select(MonitoringMember).where(MonitoringMember.dashboard_id == dashboard.id, MonitoringMember.active.is_(True))).all()
    students = [db.get(User, member.student_user_id) for member in members]
    students = [student for student in students if student]
    return {"id": str(dashboard.id), "name": dashboard.name, "description": dashboard.description, "status": dashboard.status,
            "access_code": dashboard.access_code, "leader": {"student_id": leader.student_id, "name": leader.name} if leader else None,
            "students": [monitoring_summary(student, db) for student in students], "student_count": len(students), "created_at": dashboard.created_at.isoformat()}


@app.post("/api/operator/monitoring-dashboards")
def create_monitoring_dashboard(payload: MonitoringDashboardCreate, request: Request, db: Session = Depends(get_db)):
    actor = require_operator(request, db)
    leader = db.scalar(select(User).where(User.student_id == payload.leader_student_id))
    if not leader or leader.role == "operator": raise HTTPException(404, "leader student not found")
    dashboard = MonitoringDashboard(name=payload.name.strip(), description=payload.description.strip(), leader_user_id=leader.id, created_by=actor.id, access_code=f"MON-{uuid.uuid4().hex[:10].upper()}")
    db.add(dashboard); db.flush(); audit(db, actor, "monitoring.dashboard_created", "monitoring_dashboard", str(dashboard.id), {}, {"name": dashboard.name, "leader_student_id": leader.student_id}); db.commit(); db.refresh(dashboard)
    return serialize_monitoring_dashboard(dashboard, db)


@app.get("/api/monitoring-dashboards")
def list_monitoring_dashboards(request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role == "operator": rows = db.scalars(select(MonitoringDashboard).order_by(MonitoringDashboard.created_at.desc())).all()
    else: rows = db.scalars(select(MonitoringDashboard).where(MonitoringDashboard.leader_user_id == actor.id, MonitoringDashboard.status == "active")).all()
    return [serialize_monitoring_dashboard(item, db) for item in rows]


@app.get("/api/monitoring-dashboards/{dashboard_id}")
def get_monitoring_dashboard(dashboard_id: str, request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request); dashboard = db.get(MonitoringDashboard, parse_id(dashboard_id))
    if not dashboard or (actor.role != "operator" and dashboard.leader_user_id != actor.id): raise HTTPException(404, "monitoring dashboard not found")
    return serialize_monitoring_dashboard(dashboard, db)


@app.post("/api/operator/monitoring-dashboards/{dashboard_id}/students")
def enroll_monitoring_student(dashboard_id: str, payload: MonitoringMemberCreate, request: Request, db: Session = Depends(get_db)):
    actor = require_operator(request, db); dashboard = db.get(MonitoringDashboard, parse_id(dashboard_id)); student = db.scalar(select(User).where(User.student_id == payload.student_id))
    if not dashboard or not student or student.role == "operator": raise HTTPException(404, "dashboard or student not found")
    member = db.scalar(select(MonitoringMember).where(MonitoringMember.dashboard_id == dashboard.id, MonitoringMember.student_user_id == student.id))
    if not member: db.add(MonitoringMember(dashboard_id=dashboard.id, student_user_id=student.id))
    else: member.active = True
    audit(db, actor, "monitoring.student_enrolled", "monitoring_dashboard", str(dashboard.id), {}, {"student_id": student.student_id}); db.commit()
    return serialize_monitoring_dashboard(dashboard, db)


@app.post("/api/monitoring/join/{access_code}")
def join_monitoring_dashboard(access_code: str, request: Request, db: Session = Depends(get_db)):
    student = current_user(db, request); dashboard = db.scalar(select(MonitoringDashboard).where(MonitoringDashboard.access_code == access_code, MonitoringDashboard.status == "active"))
    if not dashboard or student.role == "operator": raise HTTPException(404, "monitoring dashboard not found")
    member = db.scalar(select(MonitoringMember).where(MonitoringMember.dashboard_id == dashboard.id, MonitoringMember.student_user_id == student.id))
    if not member: db.add(MonitoringMember(dashboard_id=dashboard.id, student_user_id=student.id)); db.commit()
    return {"dashboard_id": str(dashboard.id), "status": "joined"}


def refresh_milestone(item: Milestone, db: Session) -> Milestone:
    criteria = json.loads(item.criteria_json or "{}")
    goal = db.get(Goal, item.goal_id)
    topics = [topic for phase in goal.phases for topic in phase.topics] if goal else []
    kind = criteria.get("type", "sessions"); target = max(1, float(criteria.get("target", 1)))
    if kind == "mastery": value = sum(topic.mastery >= float(criteria.get("mastery", .8)) for topic in topics)
    elif kind == "progress": value = sum(topic.progress >= float(criteria.get("progress", 1)) for topic in topics)
    else: value = len(db.scalars(select(LearningSession).where(LearningSession.goal_id == item.goal_id, LearningSession.status == "completed")).all())
    item.progress = min(1.0, value / target)
    if item.progress >= 1 and item.status != "completed": item.status = "completed"; item.completed_at = datetime.utcnow()
    return item


@app.get("/api/milestones")
def list_milestones(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goals = db.scalars(select(Goal).where(Goal.owner_id == user.id)).all(); goal_ids = [goal.id for goal in goals]
    rows = db.scalars(select(Milestone).where(Milestone.goal_id.in_(goal_ids)).order_by(Milestone.target_date, Milestone.title)).all() if goal_ids else []
    for item in rows: refresh_milestone(item, db)
    if rows: db.commit()
    return [serialize_milestone(item) for item in rows]


@app.post("/api/milestones")
def create_milestone(payload: MilestoneCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal = db.get(Goal, parse_id(payload.goal_id)) if payload.goal_id else db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if not goal or goal.owner_id != user.id: raise HTTPException(404, "goal not found")
    item = Milestone(goal_id=goal.id, title=payload.title.strip(), description=payload.description.strip(), badge_title=payload.badge_title.strip(), target_date=payload.target_date, criteria_json=json.dumps(payload.criteria))
    db.add(item); db.commit(); db.refresh(item); return serialize_milestone(item)


@app.post("/api/milestones/{milestone_id}/share")
def share_milestone(milestone_id: str, payload: MilestoneShareCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); milestone = db.get(Milestone, parse_id(milestone_id)); recipient = db.scalar(select(User).where(User.student_id == payload.recipient_student_id)); goal = db.get(Goal, milestone.goal_id) if milestone else None
    if not milestone or not recipient or not goal or goal.owner_id != user.id or recipient.id == user.id: raise HTTPException(404, "milestone or recipient not found")
    refresh_milestone(milestone, db); share = MilestoneShare(milestone_id=milestone.id, from_user_id=user.id, to_user_id=recipient.id, message=payload.message.strip()); db.add(share); db.commit(); db.refresh(share)
    return {"id": str(share.id), "recipient_student_id": recipient.student_id, "milestone": serialize_milestone(milestone), "status": "sent"}


@app.get("/api/milestone-shares")
def list_milestone_shares(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); rows = db.scalars(select(MilestoneShare).where(or_(MilestoneShare.to_user_id == user.id, MilestoneShare.from_user_id == user.id)).order_by(MilestoneShare.created_at.desc()).limit(100)).all()
    return [{"id": str(row.id), "direction": "received" if row.to_user_id == user.id else "sent", "from_student_id": db.get(User, row.from_user_id).student_id, "to_student_id": db.get(User, row.to_user_id).student_id, "message": row.message, "milestone": serialize_milestone(db.get(Milestone, row.milestone_id)), "created_at": row.created_at.isoformat()} for row in rows]


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.email.strip()
    user = db.scalar(select(User).where(or_(User.email == identifier.lower(), User.student_id == identifier.upper())))
    if not user:
        user = db.scalar(select(User).join(LearnerProfile).where(LearnerProfile.college_id == identifier))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    return {"access_token": issue_token(str(user.id), user.role), "token_type": "bearer",
            "user": {"id": str(user.id), "student_id": user.student_id, "name": user.name, "role": user.role}}


@app.post("/api/auth/bootstrap-operator")
def bootstrap_operator(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Provision the first operator using an out-of-band deployment secret."""
    configured = settings.operator_bootstrap_token
    supplied = request.headers.get("X-Operator-Bootstrap-Token")
    if not configured or supplied != configured:
        raise HTTPException(403, "operator bootstrap is not authorized")
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.role = "operator"
        user.name = payload.name.strip()
        user.password_hash = hash_password(payload.password)
    else:
        user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="operator")
        db.add(user)
    db.commit(); db.refresh(user)
    return {"access_token": issue_token(str(user.id), user.role), "token_type": "bearer",
            "user": {"id": str(user.id), "student_id": user.student_id, "name": user.name, "role": user.role}}


@app.get("/api/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal = db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if not goal: return {"user": {"name": user.name}, "goal": None, "today": []}
    topics = [t for p in goal.phases for t in p.topics]
    ranked_actions = recommendations(request, str(goal.id), db)
    today = [{"kind": item["kind"], "title": item["action"], "minutes": item["estimated_minutes"], "reason": item["reason"], "topic_id": item["topic_id"]} for item in ranked_actions[:4]]
    sessions = db.scalars(select(LearningSession).where(LearningSession.goal_id == goal.id, LearningSession.status.in_(["planned", "active"])).order_by(LearningSession.created_at.desc()).limit(8)).all()
    if not sessions:
        recent_session = db.scalar(select(LearningSession).where(LearningSession.goal_id == goal.id).order_by(LearningSession.created_at.desc()))
        if not recent_session or recent_session.created_at.date() != datetime.utcnow().date():
            for item in today[:3]:
                db.add(LearningSession(goal_id=goal.id, topic_id=parse_id(item["topic_id"]) if item.get("topic_id") else None,
                                       kind=item["kind"], planned_minutes=item["minutes"]))
            db.commit()
            sessions = db.scalars(select(LearningSession).where(LearningSession.goal_id == goal.id, LearningSession.status.in_(["planned", "active"])).order_by(LearningSession.created_at.desc()).limit(8)).all()
    return {"user": {"name": user.name}, "goal": serialize_goal(goal),
            "today": today,
            "sessions": [serialize_session(item) for item in sessions],
            "plan_status": plan_status(goal, topics),
            "stats": {"topics": len(topics), "mastered": sum(t.mastery >= .8 for t in topics),
                      "average_mastery": round(sum(t.mastery for t in topics) / len(topics), 2) if topics else 0}}


@app.get("/api/recommendations")
def recommendations(request: Request, goal_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    """Explainable next-best-action ranking: urgency, prerequisites, mastery and duration fit."""
    user = current_user(db, request)
    goal = db.get(Goal, parse_id(goal_id)) if goal_id else db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if goal and goal.owner_id != user.id:
        raise HTTPException(404, "goal not found")
    if not goal: return []
    due_reviews = db.scalars(select(ReviewItem).join(Topic).join(Phase).where(Phase.goal_id == goal.id, ReviewItem.status == "due").order_by(ReviewItem.due_at).limit(5)).all()
    topics = [t for phase in sorted(goal.phases, key=lambda p: p.order_index) for t in phase.topics]
    topic_ids = [topic.id for topic in topics]
    dependencies = db.scalars(select(TopicDependency).where(TopicDependency.topic_id.in_(topic_ids))).all() if topic_ids else []
    prerequisites_by_topic = defaultdict(list)
    for dependency in dependencies:
        prerequisites_by_topic[dependency.topic_id].append(dependency.prerequisite_topic_id)
    mastery_by_id = {topic.id: topic.mastery for topic in topics}
    result = [{"topic_id": str(item.topic_id), "action": "Review: " + item.topic.title, "kind": "review", "estimated_minutes": 8,
               "priority": "high", "reason": "scheduled retention review is due", "mastery": item.topic.mastery, "dependencies": []} for item in due_reviews]
    for index, topic in enumerate(topics):
        if topic.mastery >= .8 and topic.progress >= 1: continue
        prerequisite_ids = prerequisites_by_topic.get(topic.id, [])
        blocked_by = [item for item in prerequisite_ids if mastery_by_id.get(item, 0) < .6]
        reason = "explicit prerequisite is not yet secure" if blocked_by else ("first unfinished topic" if index == 0 else ("prerequisite sequence" if topics[index - 1].mastery < .6 else "weak mastery evidence"))
        kind = "learn" if topic.progress == 0 else "practice"
        result.append({"topic_id": str(topic.id), "action": f"{kind.title()}: {topic.title}",
                       "kind": kind, "estimated_minutes": topic.estimated_minutes if kind == "learn" else 8,
                       "priority": "high" if topic.mastery < .4 else "normal", "reason": reason,
                       "mastery": topic.mastery,
                       "dependencies": [str(item) for item in (prerequisite_ids or ([topics[index - 1].id] if index and topics[index - 1].mastery < .6 else []))]})
    return result


@app.get("/api/goals/{goal_id}/recommendations")
def goal_recommendations(goal_id: str, request: Request, db: Session = Depends(get_db)):
    return recommendations(request, goal_id, db)


@app.get("/api/knowledge-map")
def knowledge_map(request: Request, goal_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    user = current_user(db, request)
    goal = db.get(Goal, parse_id(goal_id)) if goal_id else db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if not goal or goal.owner_id != user.id:
        raise HTTPException(404, "goal not found")
    nodes = [{"id": f"goal:{goal.id}", "type": "goal", "label": goal.title}]
    edges = []
    concept_topics = defaultdict(set)
    concept_resources = defaultdict(set)
    all_topic_ids = [topic.id for phase in goal.phases for topic in phase.topics]
    dependencies = db.scalars(select(TopicDependency).where(TopicDependency.topic_id.in_(all_topic_ids))).all() if all_topic_ids else []
    for dependency in dependencies:
        edges.append({"source": f"topic:{dependency.prerequisite_topic_id}", "target": f"topic:{dependency.topic_id}", "relation": dependency.relation})
    for phase in sorted(goal.phases, key=lambda item: item.order_index):
        phase_id = f"phase:{phase.id}"
        nodes.append({"id": phase_id, "type": "phase", "label": phase.title})
        edges.append({"source": f"goal:{goal.id}", "target": phase_id, "relation": "contains"})
        for topic in phase.topics:
            topic_id = f"topic:{topic.id}"
            nodes.append({"id": topic_id, "type": "topic", "label": topic.title, "mastery": topic.mastery, "progress": topic.progress})
            edges.append({"source": phase_id, "target": topic_id, "relation": "contains"})
            for resource in topic.resources:
                resource_id = f"resource:{resource.id}"
                nodes.append({"id": resource_id, "type": "resource", "label": resource.title, "trust_status": resource.trust_status})
                edges.append({"source": topic_id, "target": resource_id, "relation": "evidence"})
                for document in resource.documents:
                    for chunk in document.chunks:
                        for term in set(semantic_terms(chunk.text)):
                            concept_topics[term].add(topic_id)
                            concept_resources[term].add(resource_id)
    ranked_concepts = sorted(concept_topics, key=lambda term: (len(concept_topics[term]), len(concept_resources[term]), term), reverse=True)[:80]
    for term in ranked_concepts:
        concept_id = f"concept:{term}"
        nodes.append({"id": concept_id, "type": "concept", "label": term, "topic_count": len(concept_topics[term]), "resource_count": len(concept_resources[term])})
        for topic_id in sorted(concept_topics[term]):
            edges.append({"source": topic_id, "target": concept_id, "relation": "aligned_concept"})
        for resource_id in sorted(concept_resources[term]):
            edges.append({"source": concept_id, "target": resource_id, "relation": "explained_by"})
    return {"goal_id": str(goal.id), "nodes": nodes, "edges": edges, "layers": ["curriculum", "semantic", "alignment"], "semantic_method": "deterministic-term-v1"}


@app.get("/api/goals/{goal_id}/semantic-concepts")
def semantic_concepts(goal_id: str, request: Request, refresh: bool = Query(default=True), db: Session = Depends(get_db)):
    """Refresh or read the goal-scoped semantic index without returning private chunk text."""
    user = current_user(db, request)
    goal = db.get(Goal, parse_id(goal_id))
    if not goal or goal.owner_id != user.id: raise HTTPException(404, "goal not found")
    if refresh:
        old_concepts = db.scalars(select(SemanticConcept).where(SemanticConcept.goal_id == goal.id)).all()
        old_ids = [concept.id for concept in old_concepts]
        if old_ids: db.execute(delete(TopicConceptAlignment).where(TopicConceptAlignment.concept_id.in_(old_ids)))
        if old_ids: db.execute(delete(SemanticConcept).where(SemanticConcept.id.in_(old_ids)))
        db.flush()
        term_sources = defaultdict(set)
        term_topics = defaultdict(set)
        chunks = db.scalars(select(ResourceChunk).join(ResourceDocument).join(Resource).where(Resource.goal_id == goal.id, Resource.trust_status != "rejected")).all()
        for chunk in chunks:
            resource = chunk.document.resource
            for term in set(semantic_terms(chunk.text)):
                term_sources[term].add(str(resource.id))
                if resource.topic_id: term_topics[term].add(resource.topic_id)
        for term, sources in sorted(term_sources.items(), key=lambda item: (len(item[1]), item[0]), reverse=True)[:200]:
            concept = SemanticConcept(goal_id=goal.id, label=term, normalized=term, source_count=len(sources), method="deterministic-term-v1")
            db.add(concept); db.flush()
            for topic_id in term_topics[term]:
                topic = db.get(Topic, topic_id)
                topic_terms = set(semantic_terms(topic.title)) if topic else set()
                score = 0.9 if term in topic_terms else 0.55
                db.add(TopicConceptAlignment(topic_id=topic_id, concept_id=concept.id, score=score, method="resource-topic-v1"))
        db.commit()
    concepts = db.scalars(select(SemanticConcept).where(SemanticConcept.goal_id == goal.id).order_by(SemanticConcept.source_count.desc()).limit(200)).all()
    concept_ids = [concept.id for concept in concepts]
    alignments = db.scalars(select(TopicConceptAlignment).where(TopicConceptAlignment.concept_id.in_(concept_ids))).all() if concept_ids else []
    return {"goal_id": str(goal.id), "concepts": [{"id": str(concept.id), "label": concept.label, "source_count": concept.source_count, "method": concept.method} for concept in concepts],
            "alignments": [{"topic_id": str(item.topic_id), "concept_id": str(item.concept_id), "score": item.score, "method": item.method} for item in alignments],
            "method": "deterministic-term-v1", "privacy": "labels-and-aggregates-only"}


@app.post("/api/tutor/ask")
def tutor_ask(payload: TutorAsk, request: Request, db: Session = Depends(get_db)):
    """Grounded tutor contract: learner-owned evidence only, citations always returned."""
    started = perf_counter()
    user = current_user(db, request)
    goal_id = parse_id(payload.goal_id) if payload.goal_id else None
    topic_id = parse_id(payload.topic_id) if payload.topic_id else None
    owned_goals = select(Goal.id).where(Goal.owner_id == user.id)
    spatial = db.get(SpatialContext, parse_id(payload.spatial_context_id)) if payload.spatial_context_id else None
    if spatial and spatial.goal_id not in [row[0] for row in db.execute(select(Goal.id).where(Goal.owner_id == user.id)).all()]:
        raise HTTPException(404, "spatial context not found")
    spatial_resolution = json.loads(spatial.resolution_json or "{}") if spatial else {}
    spatial_hint = ""
    if spatial:
        anchor_types = ", ".join(str(item.get("anchor_type")) for item in spatial_resolution.get("candidates", []) if item.get("anchor_type"))
        spatial_hint = f"\nSpatial context: selected material confidence={spatial.confidence:.2f}; surface={spatial_resolution.get('surface', 'unknown')}; structured anchors={anchor_types or 'none'}. Student asks: {spatial.utterance}"
        vision = spatial_resolution.get("vision") or {}
        if vision.get("status") == "generated":
            labels = ", ".join(str(label) for label in vision.get("labels", []))
            spatial_hint += f" Visual interpretation (model={vision.get('model', 'local')}): {vision.get('selected_region_summary', '')[:500]} Labels: {labels or 'none'}. Treat this as contextual evidence, not authority."
    query = select(ResourceChunk).join(ResourceDocument).join(Resource).where(Resource.goal_id.in_(owned_goals), Resource.trust_status != "rejected")
    if goal_id: query = query.where(Resource.goal_id == goal_id)
    if topic_id: query = query.where(or_(Resource.topic_id == topic_id, Resource.topic_id.is_(None)))
    chunks = db.scalars(query.limit(300)).all()
    qv = embed_text(payload.question + spatial_hint)
    query_terms = {term for term in re.findall(r"[a-z0-9_]+", payload.question.lower()) if len(term) > 2}
    scored_chunks = []
    for chunk in chunks:
        vector_score = cosine_similarity(qv, json.loads(chunk.embedding_json or "[]")) if chunk.embedding_json not in {"", "[]"} else 0.0
        chunk_terms = set(re.findall(r"[a-z0-9_]+", chunk.text.lower()))
        lexical_ratio = len(query_terms & chunk_terms) / len(query_terms) if query_terms else 0.0
        combined_score = max(vector_score, min(0.95, 0.10 + lexical_ratio * 0.55)) if lexical_ratio else vector_score
        scored_chunks.append((combined_score, chunk))
    ranked = sorted(scored_chunks, key=lambda item: item[0], reverse=True)
    evidence = [chunk for score, chunk in ranked if score >= .16][:5]
    citations = [{"resource": c.document.resource.title, "page": c.page, "chunk": c.ordinal,
                  "quote": c.text[:220], "score": round(next(score for score, item in ranked if item.id == c.id), 3)} for c in evidence]
    spatial_confirmation_required = bool(spatial and spatial.confidence < .8)
    sufficient = len(evidence) >= 1 and citations[0]["score"] >= .2 and not spatial_confirmation_required
    model_meta = choose_model("tutor", latency_sensitive=False).__dict__
    if sufficient:
        generated, generation_meta = grounded_completion(payload.question + spatial_hint, citations[:3])
        answer = generated or ("Here is what your saved material supports:\n\n" + "\n\n".join(f"• {item['quote']}" for item in citations[:3]))
        model_meta.update(generation_meta)
    else:
        answer = ("I need you to confirm the selected region before I use it to ground an answer."
                  if spatial_confirmation_required else
                  "I don’t have strong enough evidence in your saved material to answer reliably. Add a source or ask me to explain a specific passage.")
    record_model_event(db, "tutor", model_meta, round((perf_counter() - started) * 1000))
    db.commit()
    return {"answer": answer, "evidence_sufficient": sufficient, "spatial_confirmation_required": spatial_confirmation_required, "citations": citations,
            "spatial_context_id": str(spatial.id) if spatial else None,
            "model": model_meta, "grounding": "resource_chunks"}


@app.post("/api/tutor/ask/stream")
def tutor_ask_stream(payload: TutorAsk, request: Request, db: Session = Depends(get_db)):
    """SSE wrapper: acknowledge immediately, then emit the same grounded tutor result."""
    def events():
        yield f"event: status\ndata: {json.dumps({'status': 'retrieving_evidence'})}\n\n"
        try:
            result = tutor_ask(payload, request, db)
            yield f"event: complete\ndata: {json.dumps(result)}\n\n"
        except HTTPException as exc:
            yield f"event: error\ndata: {json.dumps({'detail': exc.detail})}\n\n"
        except Exception:
            yield f"event: error\ndata: {json.dumps({'detail': 'tutor request failed'})}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/goals")
def create_goal(payload: GoalCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal = Goal(owner_id=user.id, **payload.model_dump()); db.add(goal); db.flush()
    phase = Phase(goal_id=goal.id, title="Getting started", order_index=0); db.add(phase); db.flush()
    db.add(Topic(phase_id=phase.id, title="Define the fundamentals", description="Your first measurable topic.")); db.commit(); db.refresh(goal)
    return serialize_goal(goal)


@app.post("/api/import/learning-hq")
async def import_learning_hq(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import Learning HQ's JSON plan into normalized Goal/Phase/Topic/Resource entities."""
    user = current_user(db, request)
    try:
        plan = json.loads((await file.read()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "invalid Learning HQ JSON") from exc
    title = plan.get("meta", {}).get("title") or "Imported Learning HQ plan"
    goal = Goal(owner_id=user.id, title=title[:200], goal_type="imported", weekly_hours=8); db.add(goal); db.flush()
    phase_defs = plan.get("phases", [])
    links = plan.get("links", [])
    known = {phase.get("id"): phase for phase in phase_defs if phase.get("id")}
    for priority in dict.fromkeys([phase.get("id") for phase in phase_defs] + [link.get("priority") for link in links]):
        if not priority: continue
        phase_def = known.get(priority, {})
        phase = Phase(goal_id=goal.id, title=phase_def.get("name") or priority, order_index=len(goal.phases)); db.add(phase); db.flush()
        phase_links = [link for link in links if link.get("priority") == priority]
        for link in phase_links:
            topic = Topic(phase_id=phase.id, title=(link.get("topic") or link.get("title") or "Imported topic")[:200], description=link.get("description", ""), estimated_minutes=20)
            db.add(topic); db.flush()
            if link.get("url"):
                db.add(Resource(goal_id=goal.id, topic_id=topic.id, title=link.get("title") or link["url"], url=link["url"], source_type="imported", status="pending"))
    db.commit(); db.refresh(goal)
    return {"goal": serialize_goal(goal), "imported_phases": len(goal.phases), "imported_links": sum(1 for link in links if link.get("url"))}


@app.post("/api/topics")
def create_topic(payload: TopicCreate, request: Request, db: Session = Depends(get_db)):
    phase = db.get(Phase, parse_id(payload.phase_id))
    if not phase: raise HTTPException(404, "phase not found")
    goal = db.get(Goal, phase.goal_id); user = current_user(db, request)
    if goal.owner_id != user.id: raise HTTPException(403, "not your topic")
    topic = Topic(phase_id=phase.id, title=payload.title, description=payload.description, estimated_minutes=payload.estimated_minutes)
    db.add(topic); db.commit(); db.refresh(topic); return serialize_topic(topic)


@app.post("/api/operator/goals/{goal_id}/phases")
def operator_create_phase(goal_id: str, request: Request, title: str = Query(min_length=2, max_length=200), db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development": raise HTTPException(403, "operator role required")
    goal = db.get(Goal, parse_id(goal_id))
    if not goal: raise HTTPException(404, "goal not found")
    phase = Phase(goal_id=goal.id, title=title.strip(), order_index=max([item.order_index for item in goal.phases], default=-1) + 1)
    db.add(phase); db.flush(); audit(db, actor, "curriculum.phase_created", "phase", str(phase.id), {}, {"title": phase.title, "goal_id": str(goal.id)}); db.commit(); db.refresh(phase)
    return {"id": str(phase.id), "goal_id": str(goal.id), "title": phase.title, "order_index": phase.order_index}


@app.post("/api/operator/phases/{phase_id}/topics")
def operator_create_topic(phase_id: str, payload: TopicCreate, request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development": raise HTTPException(403, "operator role required")
    phase = db.get(Phase, parse_id(phase_id))
    if not phase: raise HTTPException(404, "phase not found")
    topic = Topic(phase_id=phase.id, title=payload.title, description=payload.description, estimated_minutes=payload.estimated_minutes)
    db.add(topic); db.flush(); audit(db, actor, "curriculum.topic_created", "topic", str(topic.id), {}, {"title": topic.title, "phase_id": str(phase.id)}); db.commit(); db.refresh(topic)
    return serialize_topic(topic)


@app.patch("/api/operator/topics/{topic_id}")
def operator_update_topic(topic_id: str, payload: TopicUpdate, request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development": raise HTTPException(403, "operator role required")
    topic = db.get(Topic, parse_id(topic_id))
    if not topic: raise HTTPException(404, "topic not found")
    before = {"title": topic.title, "description": topic.description, "difficulty": topic.difficulty, "estimated_minutes": topic.estimated_minutes}
    changes = payload.model_dump(exclude_none=True)
    for key, value in changes.items(): setattr(topic, key, value.strip() if isinstance(value, str) else value)
    audit(db, actor, "curriculum.topic_updated", "topic", str(topic.id), before, changes); db.commit(); db.refresh(topic)
    return serialize_topic(topic)


@app.post("/api/topics/{topic_id}/objectives")
def create_objective(topic_id: str, payload: ObjectiveCreate, request: Request, db: Session = Depends(get_db)):
    topic = db.get(Topic, parse_id(topic_id)); user = current_user(db, request)
    if not topic or db.get(Goal, db.get(Phase, topic.phase_id).goal_id).owner_id != user.id: raise HTTPException(404, "topic not found")
    objective = LearningObjective(topic_id=topic.id, text=payload.text, order_index=len(topic.objectives)); db.add(objective); db.commit(); db.refresh(objective)
    return {"id": str(objective.id), "topic_id": str(topic.id), "text": objective.text, "coverage": 0.0}


@app.post("/api/topics/{topic_id}/dependencies")
def create_dependency(topic_id: str, payload: DependencyCreate, request: Request, db: Session = Depends(get_db)):
    topic = db.get(Topic, parse_id(topic_id)); prerequisite = db.get(Topic, parse_id(payload.prerequisite_topic_id)); user = current_user(db, request)
    if not topic or not prerequisite: raise HTTPException(404, "topic not found")
    topic_goal = db.get(Goal, db.get(Phase, topic.phase_id).goal_id)
    prerequisite_goal = db.get(Goal, db.get(Phase, prerequisite.phase_id).goal_id)
    if topic_goal.owner_id != user.id or prerequisite_goal.owner_id != user.id or topic_goal.id != prerequisite_goal.id:
        raise HTTPException(404, "topic not found")
    if topic.id == prerequisite.id: raise HTTPException(400, "a topic cannot depend on itself")
    dependency = db.scalar(select(TopicDependency).where(TopicDependency.topic_id == topic.id, TopicDependency.prerequisite_topic_id == prerequisite.id))
    if not dependency:
        dependency = TopicDependency(topic_id=topic.id, prerequisite_topic_id=prerequisite.id, relation=payload.relation.strip() or "prerequisite_of")
        db.add(dependency); db.commit(); db.refresh(dependency)
    return {"id": str(dependency.id), "topic_id": str(topic.id), "prerequisite_topic_id": str(prerequisite.id), "relation": dependency.relation}


@app.get("/api/topics/{topic_id}/coverage")
def topic_coverage(topic_id: str, request: Request, db: Session = Depends(get_db)):
    topic = db.get(Topic, parse_id(topic_id)); user = current_user(db, request)
    if not topic or db.get(Goal, db.get(Phase, topic.phase_id).goal_id).owner_id != user.id: raise HTTPException(404, "topic not found")
    chunks = db.scalars(select(ResourceChunk).join(ResourceDocument).join(Resource).where(Resource.topic_id == topic.id)).all()
    result = []
    for objective in sorted(topic.objectives, key=lambda item: item.order_index):
        query_vector = embed_text(objective.text)
        scored = sorted(((hybrid_chunk_score(objective.text, query_vector, chunk), chunk) for chunk in chunks), key=lambda item: item[0], reverse=True)
        evidence = [(score, chunk) for score, chunk in scored if score >= .22][:5]
        best_score = evidence[0][0] if evidence else (scored[0][0] if scored else 0.0)
        result.append({"id": str(objective.id), "text": objective.text, "evidence_count": len(evidence), "coverage": round(min(1.0, best_score / .65), 2),
                       "locators": [{"page": chunk.page, "chunk": chunk.ordinal, "score": round(score, 3)} for score, chunk in evidence]})
    covered = sum(item["coverage"] >= .5 for item in result)
    return {"topic_id": str(topic.id), "coverage": round(sum(item["coverage"] for item in result) / len(result), 2) if result else 0.0, "objectives": result,
            "gap": "CONTENT_GAP" if result and covered < len(result) else None, "method": "hybrid-objective-v1"}


@app.get("/api/goals/{goal_id}/coverage")
def goal_coverage(goal_id: str, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    goal = db.get(Goal, parse_id(goal_id))
    if not goal or goal.owner_id != user.id: raise HTTPException(404, "goal not found")
    topics = [topic for phase in sorted(goal.phases, key=lambda item: item.order_index) for topic in phase.topics]
    items = []
    for topic in topics:
        coverage = topic_coverage(str(topic.id), request, db)
        items.append({"topic_id": str(topic.id), "phase_id": str(topic.phase_id), "title": topic.title,
                      "mastery": topic.mastery, "progress": topic.progress, "coverage": coverage["coverage"], "gap": coverage["gap"]})
    return {"goal_id": str(goal.id), "topics": items, "average_coverage": round(sum(item["coverage"] for item in items) / len(items), 2) if items else 0.0,
            "content_gaps": sum(item["gap"] == "CONTENT_GAP" for item in items), "method": "hybrid-objective-v1"}


@app.get("/api/operator/coverage")
def operator_coverage(request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development": raise HTTPException(403, "operator role required")
    items = []
    for topic in db.scalars(select(Topic)).all():
        chunks = db.scalars(select(ResourceChunk).join(ResourceDocument).join(Resource).where(Resource.topic_id == topic.id)).all()
        objective_results = []
        for objective in sorted(topic.objectives, key=lambda item: item.order_index):
            vector = embed_text(objective.text)
            best = max((hybrid_chunk_score(objective.text, vector, chunk) for chunk in chunks), default=0.0)
            objective_results.append(best >= .22)
        items.append({"topic_id": str(topic.id), "title": topic.title, "objectives": len(objective_results),
                      "covered_objectives": sum(objective_results), "coverage": round(sum(objective_results) / len(objective_results), 2) if objective_results else 0.0})
    return {"topics": items, "content_gaps": sum(item["objectives"] > item["covered_objectives"] for item in items),
            "average_coverage": round(sum(item["coverage"] for item in items) / len(items), 2) if items else 0.0,
            "method": "hybrid-objective-v1", "privacy": "aggregate-only"}


@app.patch("/api/topics/{topic_id}/progress")
def update_progress(topic_id: str, payload: ProgressUpdate, request: Request, db: Session = Depends(get_db)):
    topic = db.get(Topic, parse_id(topic_id)); user = current_user(db, request)
    if not topic or db.get(Goal, db.get(Phase, topic.phase_id).goal_id).owner_id != user.id: raise HTTPException(404, "topic not found")
    topic.progress = payload.progress
    if payload.mastery is not None: topic.mastery = payload.mastery
    db.commit(); return serialize_topic(topic)


def serialize_session(session: LearningSession) -> dict:
    return {"id": str(session.id), "goal_id": str(session.goal_id), "topic_id": str(session.topic_id) if session.topic_id else None,
            "topic": session.topic.title if session.topic else None, "kind": session.kind, "status": session.status,
            "planned_minutes": session.planned_minutes, "actual_minutes": session.actual_minutes, "notes": session.notes,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "created_at": session.created_at.isoformat()}


@app.get("/api/learning-sessions")
def list_learning_sessions(request: Request, status: str | None = Query(default=None), db: Session = Depends(get_db)):
    user = current_user(db, request)
    query = select(LearningSession).join(Goal).where(Goal.owner_id == user.id)
    if status: query = query.where(LearningSession.status == status)
    rows = db.scalars(query.order_by(LearningSession.created_at.desc()).limit(100)).all()
    return [serialize_session(item) for item in rows]


@app.post("/api/learning-sessions")
def create_learning_session(payload: LearningSessionCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    goal = db.get(Goal, parse_id(payload.goal_id)) if payload.goal_id else db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if not goal or goal.owner_id != user.id: raise HTTPException(404, "goal not found")
    topic = db.get(Topic, parse_id(payload.topic_id)) if payload.topic_id else None
    if topic and db.get(Phase, topic.phase_id).goal_id != goal.id: raise HTTPException(404, "topic not found")
    session = LearningSession(goal_id=goal.id, topic_id=topic.id if topic else None, kind=payload.kind.strip().lower(), planned_minutes=payload.planned_minutes)
    db.add(session); db.commit(); db.refresh(session)
    return serialize_session(session)


@app.patch("/api/learning-sessions/{session_id}")
def update_learning_session(session_id: str, payload: LearningSessionUpdate, request: Request, db: Session = Depends(get_db)):
    session = db.get(LearningSession, parse_id(session_id)); user = current_user(db, request)
    if not session or session.goal.owner_id != user.id: raise HTTPException(404, "learning session not found")
    changes = payload.model_dump(exclude_none=True)
    for key, value in changes.items():
        if key != "status": setattr(session, key, value)
    status = changes.get("status")
    if status and status not in {"planned", "active", "completed", "abandoned"}: raise HTTPException(400, "invalid session status")
    if status == "active" and not session.started_at: session.started_at = datetime.utcnow()
    if status == "completed":
        if not session.started_at: session.started_at = datetime.utcnow()
        session.completed_at = datetime.utcnow()
        if session.topic:
            session.topic.progress = max(session.topic.progress, min(1.0, session.actual_minutes / max(session.planned_minutes, 1)))
            db.add(MasteryEvidence(topic_id=session.topic.id, evidence_type="learning_session", source_id=session.id,
                                    score=min(1.0, session.actual_minutes / max(session.planned_minutes, 1)), note="completed learning session"))
    if status: session.status = status
    db.commit(); db.refresh(session)
    return serialize_session(session)


@app.post("/api/topics/{topic_id}/assessment")
def create_assessment(topic_id: str, request: Request, db: Session = Depends(get_db)):
    topic = db.get(Topic, parse_id(topic_id)); user = current_user(db, request)
    if not topic: raise HTTPException(404, "topic not found")
    phase = db.get(Phase, topic.phase_id); goal = db.get(Goal, phase.goal_id)
    if goal.owner_id != user.id: raise HTTPException(404, "topic not found")
    assessment = db.scalar(select(Assessment).where(Assessment.topic_id == topic.id))
    if not assessment:
        assessment = Assessment(topic_id=topic.id, question=f"Explain the central idea behind {topic.title} and give one practical example.", answer_key=topic.title.lower())
        db.add(assessment); db.commit(); db.refresh(assessment)
    return {"id": str(assessment.id), "topic_id": str(topic.id), "question": assessment.question, "difficulty": assessment.difficulty}


@app.post("/api/assessments/{assessment_id}/attempt")
def attempt_assessment(assessment_id: str, payload: AssessmentAttemptCreate, request: Request, db: Session = Depends(get_db)):
    assessment = db.get(Assessment, parse_id(assessment_id)); user = current_user(db, request)
    if not assessment: raise HTTPException(404, "assessment not found")
    phase = db.get(Phase, assessment.topic.phase_id); goal = db.get(Goal, phase.goal_id)
    if goal.owner_id != user.id: raise HTTPException(404, "assessment not found")
    answer = payload.answer.lower(); score = 1.0 if assessment.answer_key in answer else (0.35 if len(answer.split()) >= 12 else 0.0)
    feedback = "Strong recall evidence." if score >= .8 else "Keep the topic in review and revisit the source evidence."
    attempt = AssessmentAttempt(assessment_id=assessment.id, answer=payload.answer, score=score, feedback=feedback); db.add(attempt)
    topic = assessment.topic; topic.mastery = round(min(.95, max(topic.mastery, topic.mastery * .6 + score * .4)), 3)
    db.add(MasteryEvidence(topic_id=topic.id, evidence_type="assessment_attempt", source_id=attempt.id, score=score, note=feedback))
    review = db.scalar(select(ReviewItem).where(ReviewItem.topic_id == topic.id, ReviewItem.status == "due"))
    if not review:
        review = ReviewItem(topic_id=topic.id, interval_days=1, due_at=datetime.utcnow()); db.add(review)
    db.commit()
    return {"score": score, "feedback": feedback, "mastery": topic.mastery, "evidence": "assessment_attempt"}


@app.get("/api/review")
def review_queue(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal_ids = select(Goal.id).where(Goal.owner_id == user.id)
    rows = db.scalars(select(ReviewItem).join(Topic).join(Phase).where(Phase.goal_id.in_(goal_ids), ReviewItem.status == "due").order_by(ReviewItem.due_at).limit(50)).all()
    return [{"id": str(item.id), "topic_id": str(item.topic_id), "topic": item.topic.title, "due_at": item.due_at.isoformat(), "interval_days": item.interval_days} for item in rows]


@app.post("/api/review/{review_id}/complete")
def complete_review(review_id: str, request: Request, db: Session = Depends(get_db)):
    item = db.get(ReviewItem, parse_id(review_id)); user = current_user(db, request)
    if not item or db.get(Goal, db.get(Phase, item.topic.phase_id).goal_id).owner_id != user.id: raise HTTPException(404, "review item not found")
    item.interval_days = min(60, max(1, item.interval_days * 2)); item.due_at = datetime.utcnow() + timedelta(days=item.interval_days); item.status = "scheduled"
    db.commit(); return {"id": str(item.id), "status": item.status, "next_interval_days": item.interval_days}


@app.post("/api/resources")
def add_resource(payload: ResourceCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal = db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if not goal: raise HTTPException(400, "create a goal first")
    if payload.content.strip():
        digest = content_hash(payload.content.strip())
        duplicate = db.scalar(select(ResourceDocument).where(ResourceDocument.content_hash == digest, ResourceDocument.resource_id.in_(select(Resource.id).where(Resource.goal_id == goal.id))))
        if duplicate:
            return {"id": str(duplicate.resource_id), "title": duplicate.resource.title, "status": "duplicate", "documents": 1}
    resource = Resource(goal_id=goal.id, topic_id=parse_id(payload.topic_id) if payload.topic_id else None, **payload.model_dump(exclude={"topic_id"}))
    db.add(resource); db.flush()
    if payload.content.strip():
        text_content = payload.content.strip()
        document = ResourceDocument(resource_id=resource.id, filename=resource.title[:255], content_hash=content_hash(text_content), word_count=len(text_content.split()), status="processing")
        db.add(document); db.flush()
        parsed = type("Parsed", (), {"filename": resource.title, "content": text_content, "pages": (text_content,)})()
        for item in chunk_document(parsed):
            db.add(ResourceChunk(document_id=document.id, **item))
        document.status = "ready"
        resource.status = "ready"
    db.commit(); db.refresh(resource)
    return {"id": str(resource.id), "title": resource.title, "status": resource.status, "documents": len(resource.documents)}


@app.post("/api/resources/{resource_id}/ingest-url")
def ingest_url(resource_id: str, request: Request, db: Session = Depends(get_db)):
    resource = db.get(Resource, parse_id(resource_id)); user = current_user(db, request)
    if not resource or resource.goal.owner_id != user.id: raise HTTPException(404, "resource not found")
    if not resource.url: raise HTTPException(400, "resource has no URL")
    if settings.async_ingestion:
        job = IngestionJob(resource_id=resource.id, kind="ingest_url", status="queued", progress=0)
        resource.status = "processing"
        db.add(job); db.commit(); db.refresh(job)
        if not enqueue_optional(str(job.id), job.kind, {"resource_id": str(resource.id)}):
            job.status = "retry_pending"; job.error = "Redis unavailable; operator retry required"; db.commit()
            raise HTTPException(503, "ingestion queue unavailable")
        return {"resource_id": str(resource.id), "job_id": str(job.id), "status": "queued"}
    try:
        text = fetch_web_text(resource.url)
    except ValueError as exc:
        resource.status = "failed"; db.commit(); raise HTTPException(400, str(exc)) from exc
    if not text:
        resource.status = "failed"; db.commit()
        raise HTTPException(422, "no readable text found")
    digest = content_hash(text)
    existing = db.scalar(select(ResourceDocument).where(ResourceDocument.content_hash == digest, ResourceDocument.resource_id.in_(select(Resource.id).where(Resource.goal_id == resource.goal_id)), ResourceDocument.resource_id != resource.id))
    if existing:
        resource.status = "duplicate"; db.commit()
        return {"resource_id": str(existing.resource_id), "document_id": str(existing.id), "status": "duplicate", "chunks": len(existing.chunks), "word_count": existing.word_count}
    resource.content = text; resource.status = "ready"
    document = ResourceDocument(resource_id=resource.id, filename=resource.title[:255], content_hash=digest, word_count=len(text.split()), status="processing")
    db.add(document); db.flush()
    for item in chunk_document(type("Parsed", (), {"filename": resource.title, "content": text, "pages": (text,)})()): db.add(ResourceChunk(document_id=document.id, **item))
    document.status = "ready"; db.commit(); db.refresh(document)
    return {"resource_id": str(resource.id), "document_id": str(document.id), "status": "ready", "chunks": len(document.chunks), "word_count": document.word_count}


@app.post("/api/resources/{resource_id}/ingest-github")
def ingest_github(resource_id: str, request: Request, db: Session = Depends(get_db)):
    """Ingest a public repository README through the bounded GitHub adapter."""
    resource = db.get(Resource, parse_id(resource_id)); user = current_user(db, request)
    if not resource or resource.goal.owner_id != user.id: raise HTTPException(404, "resource not found")
    if not settings.feature_github_ingestion: raise HTTPException(404, "GitHub ingestion is disabled")
    if not resource.url: raise HTTPException(400, "resource has no GitHub URL")
    if settings.async_ingestion:
        job = IngestionJob(resource_id=resource.id, kind="ingest_github", status="queued", progress=0)
        resource.status = "processing"; db.add(job); db.commit(); db.refresh(job)
        if not enqueue_optional(str(job.id), job.kind, {"resource_id": str(resource.id)}):
            job.status = "retry_pending"; job.error = "Redis unavailable; operator retry required"; db.commit()
            raise HTTPException(503, "ingestion queue unavailable")
        return {"resource_id": str(resource.id), "job_id": str(job.id), "status": "queued"}
    try:
        text = fetch_github_text(resource.url)
    except ValueError as exc:
        resource.status = "failed"; db.commit(); raise HTTPException(400, str(exc)) from exc
    if not text:
        resource.status = "failed"; db.commit(); raise HTTPException(422, "repository README is empty")
    digest = content_hash(text)
    existing = db.scalar(select(ResourceDocument).where(ResourceDocument.content_hash == digest, ResourceDocument.resource_id.in_(select(Resource.id).where(Resource.goal_id == resource.goal_id)), ResourceDocument.resource_id != resource.id))
    if existing:
        resource.status = "duplicate"; db.commit()
        return {"resource_id": str(existing.resource_id), "document_id": str(existing.id), "status": "duplicate", "chunks": len(existing.chunks)}
    resource.content = text; resource.status = "ready"
    document = ResourceDocument(resource_id=resource.id, filename=resource.title[:255], content_hash=digest, word_count=len(text.split()), status="processing")
    db.add(document); db.flush()
    for item in chunk_document(type("Parsed", (), {"filename": resource.title, "content": text, "pages": (text,)})()): db.add(ResourceChunk(document_id=document.id, **item))
    document.status = "ready"; db.commit(); db.refresh(document)
    return {"resource_id": str(resource.id), "document_id": str(document.id), "status": "ready", "chunks": len(document.chunks), "word_count": document.word_count}


@app.post("/api/resources/{resource_id}/ingest-youtube")
def ingest_youtube(resource_id: str, request: Request, db: Session = Depends(get_db)):
    """Ingest captions only; video media is never downloaded or persisted."""
    resource = db.get(Resource, parse_id(resource_id)); user = current_user(db, request)
    if not resource or resource.goal.owner_id != user.id: raise HTTPException(404, "resource not found")
    if not settings.feature_youtube_ingestion: raise HTTPException(404, "YouTube ingestion is disabled")
    if not resource.url: raise HTTPException(400, "resource has no YouTube URL")
    if settings.async_ingestion:
        job = IngestionJob(resource_id=resource.id, kind="ingest_youtube", status="queued", progress=0)
        resource.status = "processing"; db.add(job); db.commit(); db.refresh(job)
        if not enqueue_optional(str(job.id), job.kind, {"resource_id": str(resource.id)}):
            job.status = "retry_pending"; job.error = "Redis unavailable; operator retry required"; db.commit()
            raise HTTPException(503, "ingestion queue unavailable")
        return {"resource_id": str(resource.id), "job_id": str(job.id), "status": "queued"}
    try:
        text = fetch_youtube_transcript(resource.url)
    except ValueError as exc:
        resource.status = "failed"; db.commit(); raise HTTPException(400, str(exc)) from exc
    digest = content_hash(text)
    existing = db.scalar(select(ResourceDocument).where(ResourceDocument.content_hash == digest, ResourceDocument.resource_id.in_(select(Resource.id).where(Resource.goal_id == resource.goal_id)), ResourceDocument.resource_id != resource.id))
    if existing:
        resource.status = "duplicate"; db.commit()
        return {"resource_id": str(existing.resource_id), "document_id": str(existing.id), "status": "duplicate", "chunks": len(existing.chunks)}
    resource.content = text; resource.status = "ready"
    document = ResourceDocument(resource_id=resource.id, filename=resource.title[:255], content_hash=digest, word_count=len(text.split()), status="processing")
    db.add(document); db.flush()
    for item in chunk_document(type("Parsed", (), {"filename": resource.title, "content": text, "pages": (text,)})()): db.add(ResourceChunk(document_id=document.id, **item))
    document.status = "ready"; db.commit(); db.refresh(document)
    return {"resource_id": str(resource.id), "document_id": str(document.id), "status": "ready", "chunks": len(document.chunks), "word_count": document.word_count}


@app.post("/api/resources/upload")
async def upload_resource(request: Request, file: UploadFile = File(...), topic_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    user = current_user(db, request); goal = db.scalar(select(Goal).where(Goal.owner_id == user.id).order_by(Goal.status))
    if not goal: raise HTTPException(400, "create a goal first")
    filename = Path(file.filename or "upload.txt").name
    raw_payload = await file.read()
    if len(raw_payload) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"file exceeds the {settings.max_upload_mb} MB upload limit")
    if settings.async_ingestion:
        import hashlib
        storage_key = f"{hashlib.sha256(raw_payload).hexdigest()}-{filename}"
        resource = Resource(goal_id=goal.id, topic_id=parse_id(topic_id) if topic_id else None, title=filename, source_type="file", content="", status="processing")
        db.add(resource); db.flush()
        job = IngestionJob(resource_id=resource.id, status="queued", progress=0, storage_key=storage_key)
        db.add(job); db.commit(); db.refresh(job)
        try:
            put_bytes(storage_key, raw_payload)
        except Exception as exc:
            resource.status = "failed"; job.status = "failed"; job.error = f"object storage write failed: {exc}"[:1000]
            db.commit()
            raise HTTPException(503, "object storage unavailable") from exc
        if not enqueue_optional(str(job.id), job.kind, {"resource_id": str(resource.id), "storage_key": storage_key, "filename": filename}):
            job.status = "retry_pending"; job.error = "Redis unavailable; operator retry required"; db.commit()
            raise HTTPException(503, "ingestion queue unavailable")
        return {"resource_id": str(resource.id), "job_id": str(job.id), "status": "queued", "chunks": 0}
    try:
        parsed = parse_document(filename, raw_payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    digest = content_hash(parsed.content)
    existing = db.scalar(select(ResourceDocument).where(ResourceDocument.content_hash == digest, ResourceDocument.resource_id.in_(select(Resource.id).where(Resource.goal_id == goal.id))))
    if existing:
        return {"resource_id": str(existing.resource_id), "document_id": str(existing.id), "status": "duplicate", "chunks": len(existing.chunks)}
    resource = Resource(goal_id=goal.id, topic_id=parse_id(topic_id) if topic_id else None, title=filename, source_type="file", content=parsed.content, status="ready")
    db.add(resource); db.flush()
    job = IngestionJob(resource_id=resource.id, status="processing", progress=10); db.add(job); db.flush()
    document = ResourceDocument(resource_id=resource.id, filename=filename, content_hash=digest, word_count=len(parsed.content.split()), status="processing")
    db.add(document); db.flush()
    for item in chunk_document(parsed):
        db.add(ResourceChunk(document_id=document.id, **item))
    document.status = "ready"; job.status = "completed"; job.progress = 100
    db.commit(); db.refresh(document)
    return {"resource_id": str(resource.id), "document_id": str(document.id), "job_id": str(job.id), "status": job.status, "chunks": len(document.chunks), "word_count": document.word_count}


@app.get("/api/ingestion/jobs")
def ingestion_jobs(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    rows = db.scalars(select(IngestionJob).join(Resource).where(Resource.goal_id.in_(select(Goal.id).where(Goal.owner_id == user.id))).order_by(IngestionJob.created_at.desc()).limit(50)).all()
    return [{"id": str(job.id), "resource_id": str(job.resource_id), "kind": job.kind, "status": job.status, "progress": job.progress, "error": job.error} for job in rows]


@app.post("/api/operator/ingestion/{job_id}/retry")
def retry_ingestion(job_id: str, request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development":
        raise HTTPException(403, "operator role required")
    job = db.get(IngestionJob, parse_id(job_id))
    if not job: raise HTTPException(404, "ingestion job not found")
    before = {"status": job.status, "progress": job.progress}
    job.status = "queued"; job.progress = 0; job.error = ""; job.updated_at = datetime.utcnow()
    resource = db.get(Resource, job.resource_id)
    retry_payload = {"resource_id": str(job.resource_id), "retry": True}
    if resource:
        retry_payload.update({"filename": resource.title, "storage_key": job.storage_key})
    enqueued = enqueue_optional(str(job.id), job.kind, retry_payload)
    if not enqueued: job.status = "retry_pending"
    audit(db, actor, "ingestion.retry", "ingestion_job", str(job.id), before, {"status": job.status, "progress": job.progress}); db.commit()
    return {"id": str(job.id), "status": job.status, "enqueued": enqueued}


@app.get("/api/search")
def search(request: Request, q: str = Query(min_length=2), db: Session = Depends(get_db)):
    user = current_user(db, request); needle = f"%{q}%"
    query_vector = embed_text(q)
    chunk_query = select(ResourceChunk).join(ResourceDocument).join(Resource).where(Resource.goal_id.in_(select(Goal.id).where(Goal.owner_id == user.id)), Resource.trust_status != "rejected")
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        chunks = db.scalars(chunk_query.order_by(ResourceChunk.embedding.cosine_distance(query_vector)).limit(50)).all()
    else:
        chunks = db.scalars(chunk_query.limit(300)).all()
    ranked = sorted(chunks, key=lambda c: cosine_similarity(query_vector, json.loads(c.embedding_json or "[]")) if c.embedding_json not in {"", "[]"} else 0, reverse=True)
    relevant = [c for c in ranked if q.lower() in c.text.lower() or (c.embedding_json not in {"", "[]"} and cosine_similarity(query_vector, json.loads(c.embedding_json)) > .18)][:20]
    if relevant:
        return [{"id": str(c.id), "resource_id": str(c.document.resource_id), "title": c.document.resource.title, "source_type": c.document.resource.source_type,
                 "snippet": c.text[:320], "score": round(cosine_similarity(query_vector, json.loads(c.embedding_json or "[]")), 3), "locator": {"page": c.page, "chunk": c.ordinal}} for c in relevant]
    rows = db.scalars(select(Resource).where(Resource.goal_id.in_(select(Goal.id).where(Goal.owner_id == user.id)), or_(Resource.title.ilike(needle), Resource.content.ilike(needle))).limit(20)).all()
    return [{"id": str(r.id), "title": r.title, "source_type": r.source_type, "snippet": r.content[:240]} for r in rows]


@app.post("/api/spatial-context")
def save_spatial_context(payload: SpatialContextCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal = db.get(Goal, parse_id(payload.goal_id))
    if not goal or goal.owner_id != user.id: raise HTTPException(404, "goal not found")
    if not payload.marks: raise HTTPException(400, "at least one mark is required")
    resolution = resolve_spatial_marks(payload.marks, payload.canvas, payload.anchors, payload.image_data, payload.utterance)
    resolution.update({"surface": payload.surface, "crop_ref": payload.crop_ref, "privacy_policy": payload.privacy_policy})
    record_model_event(db, "spatial_resolve", choose_model("spatial_resolve", latency_sensitive=True).__dict__, resolution["latency_ms"], resolution["confidence"])
    context = SpatialContext(goal_id=goal.id, utterance=payload.utterance, marks_json=json.dumps(payload.marks), source=payload.source,
                             sensitivity_class="private", confidence=resolution["confidence"],
                             resolution_json=json.dumps(resolution), processing_ms=resolution["latency_ms"])
    db.add(context); db.commit(); db.refresh(context)
    return {"id": str(context.id), "message": "Spatial context saved. It can now ground tutor or recommendation actions.",
            "marks": len(payload.marks), "confidence": context.confidence, "resolution": resolution,
            "model": choose_model("spatial_resolve", latency_sensitive=True).__dict__}


@app.post("/api/spatial-context/resolve")
def resolve_spatial_context(payload: SpatialContextCreate, request: Request):
    """Fast preview path: no DB write, safe to call while the user is still interacting."""
    current = resolve_spatial_marks(payload.marks, payload.canvas, payload.anchors, payload.image_data, payload.utterance)
    return {"utterance": payload.utterance, "resolution": current,
            "model": choose_model("spatial_resolve", latency_sensitive=True).__dict__,
            "persisted": False}


@app.get("/api/operator/overview")
def operator_overview(request: Request, db: Session = Depends(get_db)):
    """Operator metadata only; private resource text and spatial pixels never appear here."""
    actor = current_user(db, request)
    if actor.role != "operator" and request.headers.get("Authorization") and settings.environment != "development":
        raise HTTPException(403, "operator role required")
    users = len(db.scalars(select(User)).all())
    goals = db.scalars(select(Goal)).all()
    topics = db.scalars(select(Topic)).all()
    resources = db.scalars(select(Resource)).all()
    contexts = db.scalars(select(SpatialContext)).all()
    sessions = db.scalars(select(LearningSession)).all()
    packages = db.scalars(select(LearningPackage)).all()
    dashboards = db.scalars(select(MonitoringDashboard)).all()
    return {"users": users, "goals": len(goals), "topics": len(topics), "resources": len(resources),
            "ingestion_ready": sum(r.status == "ready" for r in resources),
            "documents": len(db.scalars(select(ResourceDocument)).all()),
            "chunks": len(db.scalars(select(ResourceChunk)).all()),
            "ingestion_jobs": len(db.scalars(select(IngestionJob)).all()),
            "spatial_contexts": len(contexts), "learning_sessions": len(sessions), "completed_sessions": sum(s.status == "completed" for s in sessions),
            "packages": len(packages), "published_packages": sum(item.status == "published" for item in packages), "monitoring_dashboards": len(dashboards),
            "spatial_avg_confidence": round(sum(c.confidence for c in contexts) / len(contexts), 2) if contexts else 0,
            "spatial_low_confidence": sum(c.confidence < .7 for c in contexts),
            "spatial_avg_latency_ms": round(sum(c.processing_ms for c in contexts) / len(contexts)) if contexts else 0,
            "model_routes": {task: choose_model(task, task == "spatial_resolve").__dict__ for task in ["spatial_resolve", "tutor", "assessment", "recommendation"]},
            "privacy": "private document text is excluded from operator aggregates"}


@app.get("/api/operator/snapshot")
def operator_snapshot(request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development":
        raise HTTPException(403, "operator role required")
    goals = db.scalars(select(Goal)).all()
    users = db.scalars(select(User)).all()
    resources = db.scalars(select(Resource)).all()
    jobs = db.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(25)).all()
    spatial = db.scalars(select(SpatialContext).where(SpatialContext.confidence < .7).order_by(SpatialContext.created_at.desc()).limit(25)).all()
    audits = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)).all()
    packages = db.scalars(select(LearningPackage).order_by(LearningPackage.updated_at.desc()).limit(50)).all()
    dashboards = db.scalars(select(MonitoringDashboard).order_by(MonitoringDashboard.created_at.desc()).limit(50)).all()
    return {
        "users": [{"id": str(u.id), "name": u.name, "role": u.role, "created_at": u.created_at.isoformat()} for u in users],
        "goals": [{"id": str(g.id), "title": g.title, "owner_id": str(g.owner_id), "status": g.status,
                   "topics": sum(len(p.topics) for p in g.phases), "resources": len(g.resources)} for g in goals],
        "resources": [{"id": str(r.id), "title": r.title, "source_type": r.source_type, "status": r.status,
                       "trust_status": r.trust_status, "has_content": bool(r.content), "document_count": len(r.documents)} for r in resources],
        "ingestion_jobs": [{"id": str(j.id), "resource_id": str(j.resource_id), "kind": j.kind, "status": j.status, "progress": j.progress, "error": j.error} for j in jobs],
        "spatial_review": [{"id": str(s.id), "goal_id": str(s.goal_id), "confidence": s.confidence,
                            "processing_ms": s.processing_ms, "utterance_preview": s.utterance[:160]} for s in spatial],
        "audit_log": [{"id": str(a.id), "actor_id": str(a.actor_id), "action": a.action, "entity_type": a.entity_type,
                       "entity_id": a.entity_id, "created_at": a.created_at.isoformat()} for a in audits],
        "packages": [{"id": str(item.id), "slug": item.slug, "title": item.title, "version": item.version, "status": item.status, "updated_at": item.updated_at.isoformat()} for item in packages],
        "monitoring_dashboards": [{"id": str(item.id), "name": item.name, "status": item.status, "access_code": item.access_code} for item in dashboards],
        "privacy": {"raw_resource_text": False, "raw_screen_pixels": False, "operator_access": "metadata_and_quality_signals"},
    }


@app.get("/api/operator/analytics")
def operator_analytics(request: Request, db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development": raise HTTPException(403, "operator role required")
    topics = db.scalars(select(Topic)).all(); resources = db.scalars(select(Resource)).all(); jobs = db.scalars(select(IngestionJob)).all(); contexts = db.scalars(select(SpatialContext)).all(); attempts = db.scalars(select(AssessmentAttempt)).all(); reviews = db.scalars(select(ReviewItem)).all(); sessions = db.scalars(select(LearningSession)).all()
    latencies = [context.processing_ms for context in contexts]
    corrections = db.scalars(select(SpatialCorrection)).all()
    model_events = db.scalars(select(ModelEvent).order_by(ModelEvent.created_at.desc()).limit(2000)).all()
    model_by_task = {}
    for event in model_events:
        model_by_task.setdefault(event.task, []).append(event)
    model_runtime = {}
    for task, events in model_by_task.items():
        latencies_for_task = [event.latency_ms for event in events]
        model_runtime[task] = {"count": len(events), "p50_latency_ms": percentile(latencies_for_task, .50),
                               "p95_latency_ms": percentile(latencies_for_task, .95),
                               "fallback_rate": round(sum(event.status == "fallback" for event in events) / len(events), 3),
                               "failures": sum(event.status in {"error", "failed"} for event in events),
                               "providers": sorted({event.provider for event in events})}
    return {
        "mastery_buckets": {"not_started": sum(t.mastery == 0 for t in topics), "developing": sum(0 < t.mastery < .8 for t in topics), "mastered": sum(t.mastery >= .8 for t in topics)},
        "resource_trust": {status: sum(r.trust_status == status for r in resources) for status in ["verified", "unverified", "rejected"]},
        "ingestion_status": {status: sum(j.status == status for j in jobs) for status in ["queued", "processing", "completed", "failed", "retry_pending"]},
        "spatial": {"count": len(contexts), "low_confidence": sum(c.confidence < .7 for c in contexts), "avg_confidence": round(sum(c.confidence for c in contexts) / len(contexts), 3) if contexts else 0, "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0, "p50_latency_ms": percentile(latencies, .50), "p95_latency_ms": percentile(latencies, .95), "max_latency_ms": max(latencies) if latencies else 0},
        "quality": {"ingestion_failure_rate": round(sum(job.status in {"failed", "retry_pending"} for job in jobs) / len(jobs), 3) if jobs else 0, "trusted_resources": sum(resource.trust_status == "verified" for resource in resources), "spatial_corrections": len(corrections), "spatial_correction_rate": round(len(corrections) / len(contexts), 3) if contexts else 0},
        "assessment": {"attempts": len(attempts), "average_score": round(sum(item.score for item in attempts) / len(attempts), 3) if attempts else 0},
        "review": {"due": sum(item.status == "due" for item in reviews), "scheduled": sum(item.status == "scheduled" for item in reviews)},
        "sessions": {"total": len(sessions), "planned": sum(item.status == "planned" for item in sessions), "active": sum(item.status == "active" for item in sessions), "completed": sum(item.status == "completed" for item in sessions), "minutes": sum(item.actual_minutes for item in sessions)},
        "model_health": {"embedding_backend": "ollama" if settings.local_llm_base_url else ("sentence-transformer" if settings.use_local_embeddings else "deterministic-fallback"), "local_embedding_enabled": settings.use_local_embeddings, "tutor_route": choose_model("tutor").__dict__, "spatial_route": choose_model("spatial_resolve", latency_sensitive=True).__dict__, "vision_route": {"provider": "local", "model": settings.local_vision_model or "not-configured", "optional": True}, "cloud_fallback_configured": bool(settings.openai_api_key or settings.anthropic_api_key), "runtime": model_runtime},
        "privacy": "aggregates only; private text and pixels excluded",
    }


@app.patch("/api/operator/resources/{resource_id}/trust")
def update_resource_trust(resource_id: str, request: Request, status: str = Query(...), db: Session = Depends(get_db)):
    actor = current_user(db, request)
    if actor.role != "operator" and settings.environment != "development": raise HTTPException(403, "operator role required")
    if status not in {"verified", "unverified", "rejected"}: raise HTTPException(400, "invalid trust status")
    resource = db.get(Resource, parse_id(resource_id))
    if not resource: raise HTTPException(404, "resource not found")
    before = {"trust_status": resource.trust_status}; resource.trust_status = status; resource.updated_at = datetime.utcnow()
    audit(db, actor, "resource.trust_changed", "resource", str(resource.id), before, {"trust_status": status}); db.commit()
    return {"id": str(resource.id), "trust_status": resource.trust_status}


@app.get("/api/spatial-context")
def list_spatial_context(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request); goal_ids = select(Goal.id).where(Goal.owner_id == user.id)
    rows = db.scalars(select(SpatialContext).where(SpatialContext.goal_id.in_(goal_ids)).order_by(SpatialContext.created_at.desc()).limit(10)).all()
    return [{"id": str(r.id), "utterance": r.utterance, "marks": json.loads(r.marks_json), "created_at": r.created_at.isoformat()} for r in rows]


@app.post("/api/spatial-context/{context_id}/correct")
def correct_spatial_context(context_id: str, payload: SpatialCorrectionCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    context = db.get(SpatialContext, parse_id(context_id))
    if not context or db.scalar(select(Goal).where(Goal.id == context.goal_id, Goal.owner_id == user.id)) is None:
        raise HTTPException(404, "spatial context not found")
    if not payload.marks:
        raise HTTPException(400, "at least one corrected mark is required")
    resolution = resolve_spatial_marks(payload.marks, payload.canvas)
    resolution["resolver"] = "user-correction-v1"
    resolution["confidence"] = max(resolution["confidence"], 0.99)
    correction = SpatialCorrection(context_id=context.id, corrected_marks_json=json.dumps(payload.marks), note=payload.note)
    context.marks_json = json.dumps(payload.marks)
    context.resolution_json = json.dumps(resolution)
    context.confidence = resolution["confidence"]
    context.processing_ms = resolution["latency_ms"]
    db.add(correction); db.commit(); db.refresh(correction)
    return {"id": str(correction.id), "context_id": str(context.id), "confidence": context.confidence, "resolution": resolution}


@app.get("/api/me/export")
def export_student_data(request: Request, db: Session = Depends(get_db)):
    """Return the authenticated student's learning data without exposing other users."""
    user = current_user(db, request)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    goals = db.scalars(select(Goal).where(Goal.owner_id == user.id)).all()
    goal_ids = {goal.id for goal in goals}
    resources = db.scalars(select(Resource).where(Resource.goal_id.in_(goal_ids))).all() if goal_ids else []
    contexts = db.scalars(select(SpatialContext).where(SpatialContext.goal_id.in_(goal_ids))).all() if goal_ids else []
    sessions = db.scalars(select(LearningSession).where(LearningSession.goal_id.in_(goal_ids)).order_by(LearningSession.created_at)).all() if goal_ids else []
    return {
        "user": {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role},
        "profile": serialize_profile(profile) if profile else None,
        "goals": [serialize_goal(goal) for goal in goals],
        "learning_sessions": [serialize_session(session) for session in sessions],
        "resources": [{"id": str(resource.id), "title": resource.title, "url": resource.url,
                       "source_type": resource.source_type, "content": resource.content,
                       "status": resource.status, "trust_status": resource.trust_status} for resource in resources],
        "spatial_contexts": [{"id": str(context.id), "goal_id": str(context.goal_id),
                              "utterance": context.utterance, "marks": json.loads(context.marks_json),
                              "resolution": json.loads(context.resolution_json),
                              "created_at": context.created_at.isoformat()} for context in contexts],
    }


@app.delete("/api/me")
def delete_student_account(request: Request, confirm: str = Query(default=""), db: Session = Depends(get_db)):
    """Permanently delete one student's owned learning data after explicit confirmation."""
    if confirm != "DELETE":
        raise HTTPException(400, "confirm account deletion with ?confirm=DELETE")
    user = current_user(db, request)
    goals = db.scalars(select(Goal).where(Goal.owner_id == user.id)).all()
    goal_ids = [goal.id for goal in goals]
    topic_ids = [topic.id for goal in goals for phase in goal.phases for topic in phase.topics]
    resource_ids = [resource.id for goal in goals for resource in goal.resources]
    db.execute(delete(LearningSession).where(LearningSession.goal_id.in_(goal_ids))) if goal_ids else None
    milestone_ids = [item.id for item in db.scalars(select(Milestone).where(Milestone.goal_id.in_(goal_ids))).all()] if goal_ids else []
    if milestone_ids: db.execute(delete(MilestoneShare).where(MilestoneShare.milestone_id.in_(milestone_ids)))
    if milestone_ids: db.execute(delete(Milestone).where(Milestone.id.in_(milestone_ids)))
    if goal_ids: db.execute(delete(PackageInstall).where(or_(PackageInstall.user_id == user.id, PackageInstall.goal_id.in_(goal_ids))))
    led_dashboard_ids = [item.id for item in db.scalars(select(MonitoringDashboard).where(MonitoringDashboard.leader_user_id == user.id)).all()]
    db.execute(delete(MonitoringMember).where(or_(MonitoringMember.student_user_id == user.id, MonitoringMember.dashboard_id.in_(led_dashboard_ids))))
    db.execute(delete(MonitoringDashboard).where(MonitoringDashboard.leader_user_id == user.id))
    db.execute(delete(MilestoneShare).where(or_(MilestoneShare.from_user_id == user.id, MilestoneShare.to_user_id == user.id)))
    context_ids = [context.id for context in db.scalars(select(SpatialContext).where(SpatialContext.goal_id.in_(goal_ids))).all()] if goal_ids else []
    concept_ids = [concept.id for concept in db.scalars(select(SemanticConcept).where(SemanticConcept.goal_id.in_(goal_ids))).all()] if goal_ids else []
    assessment_ids = [assessment.id for assessment in db.scalars(select(Assessment).where(Assessment.topic_id.in_(topic_ids))).all()] if topic_ids else []
    document_ids = [document.id for document in db.scalars(select(ResourceDocument).where(ResourceDocument.resource_id.in_(resource_ids))).all()] if resource_ids else []
    if context_ids: db.execute(delete(SpatialCorrection).where(SpatialCorrection.context_id.in_(context_ids)))
    if context_ids: db.execute(delete(SpatialContext).where(SpatialContext.id.in_(context_ids)))
    if concept_ids: db.execute(delete(TopicConceptAlignment).where(TopicConceptAlignment.concept_id.in_(concept_ids)))
    if concept_ids: db.execute(delete(SemanticConcept).where(SemanticConcept.id.in_(concept_ids)))
    if assessment_ids: db.execute(delete(AssessmentAttempt).where(AssessmentAttempt.assessment_id.in_(assessment_ids)))
    if assessment_ids: db.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
    if topic_ids:
        db.execute(delete(TopicDependency).where(or_(TopicDependency.topic_id.in_(topic_ids), TopicDependency.prerequisite_topic_id.in_(topic_ids))))
        db.execute(delete(MasteryEvidence).where(MasteryEvidence.topic_id.in_(topic_ids)))
        db.execute(delete(ReviewItem).where(ReviewItem.topic_id.in_(topic_ids)))
        db.execute(delete(LearningObjective).where(LearningObjective.topic_id.in_(topic_ids)))
    if document_ids: db.execute(delete(ResourceChunk).where(ResourceChunk.document_id.in_(document_ids)))
    if resource_ids:
        db.execute(delete(ResourceDocument).where(ResourceDocument.id.in_(document_ids)))
        db.execute(delete(IngestionJob).where(IngestionJob.resource_id.in_(resource_ids)))
        db.execute(delete(Resource).where(Resource.id.in_(resource_ids)))
    if topic_ids: db.execute(delete(Topic).where(Topic.id.in_(topic_ids)))
    if goal_ids:
        db.execute(delete(Phase).where(Phase.goal_id.in_(goal_ids)))
        db.execute(delete(Goal).where(Goal.id.in_(goal_ids)))
    db.execute(delete(AuditLog).where(AuditLog.actor_id == user.id))
    db.delete(user); db.commit()
    return {"status": "deleted"}


static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
