from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.types import GUID, VectorPortable


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"STU-{uuid.uuid4().hex[:10].upper()}")
    name: Mapped[str] = mapped_column(String(120), default="Student")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(30), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    goals: Mapped[list[Goal]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    profile: Mapped[LearnerProfile | None] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    education_stage: Mapped[str] = mapped_column(String(40), default="other")
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_skill_level: Mapped[str] = mapped_column(String(40), default="beginner")
    known_skills_json: Mapped[str] = mapped_column(Text, default="[]")
    learning_modes_json: Mapped[str] = mapped_column(Text, default="[\"mixed\"]")
    preferred_pace: Mapped[str] = mapped_column(String(30), default="steady")
    constraints: Mapped[str] = mapped_column(Text, default="")
    college_name: Mapped[str] = mapped_column(String(200), default="")
    college_year: Mapped[str] = mapped_column(String(40), default="")
    branch: Mapped[str] = mapped_column(String(120), default="")
    college_id: Mapped[str] = mapped_column(String(120), default="")
    coding_profiles_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[User] = relationship(back_populates="profile")


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    goal_type: Mapped[str] = mapped_column(String(40), default="custom")
    target_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    weekly_hours: Mapped[int] = mapped_column(Integer, default=8)
    status: Mapped[str] = mapped_column(String(30), default="active")
    owner: Mapped[User] = relationship(back_populates="goals")
    phases: Mapped[list[Phase]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    resources: Mapped[list[Resource]] = relationship(back_populates="goal", cascade="all, delete-orphan")


class Phase(Base):
    __tablename__ = "phases"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    goal: Mapped[Goal] = relationship(back_populates="phases")
    topics: Mapped[list[Topic]] = relationship(back_populates="phase", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("phases.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(30), default="intermediate")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    phase: Mapped[Phase] = relationship(back_populates="topics")
    resources: Mapped[list[Resource]] = relationship(back_populates="topic")
    objectives: Mapped[list[LearningObjective]] = relationship(back_populates="topic", cascade="all, delete-orphan")


class TopicDependency(Base):
    __tablename__ = "topic_dependencies"
    __table_args__ = (UniqueConstraint("topic_id", "prerequisite_topic_id", name="uq_topic_dependency"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    prerequisite_topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    relation: Mapped[str] = mapped_column(String(40), default="prerequisite_of")


class SemanticConcept(Base):
    __tablename__ = "semantic_concepts"
    __table_args__ = (UniqueConstraint("goal_id", "normalized", name="uq_goal_semantic_concept"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    label: Mapped[str] = mapped_column(String(160))
    normalized: Mapped[str] = mapped_column(String(160))
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(50), default="deterministic-term-v1")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TopicConceptAlignment(Base):
    __tablename__ = "topic_concept_alignments"
    __table_args__ = (UniqueConstraint("topic_id", "concept_id", name="uq_topic_concept_alignment"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("semantic_concepts.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    method: Mapped[str] = mapped_column(String(50), default="resource-topic-v1")


class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    topic: Mapped[Topic] = relationship(back_populates="objectives")


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("goal_id", "url", name="uq_goal_resource_url"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30), default="link")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="ready")
    trust_status: Mapped[str] = mapped_column(String(30), default="unverified")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    goal: Mapped[Goal] = relationship(back_populates="resources")
    topic: Mapped[Topic | None] = relationship(back_populates="resources")
    documents: Mapped[list[ResourceDocument]] = relationship(back_populates="resource", cascade="all, delete-orphan")


class ResourceDocument(Base):
    __tablename__ = "resource_documents"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="ready")
    resource: Mapped[Resource] = relationship(back_populates="documents")
    chunks: Mapped[list[ResourceChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class ResourceChunk(Base):
    __tablename__ = "resource_chunks"
    __table_args__ = (Index("ix_resource_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resource_documents.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")
    embedding: Mapped[list[float] | None] = mapped_column(VectorPortable(384), nullable=True)
    heading: Mapped[str] = mapped_column(String(255), default="")
    page: Mapped[int] = mapped_column(Integer, default=1)
    document: Mapped[ResourceDocument] = relationship(back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50), default="parse_chunk_embed")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    progress: Mapped[int] = mapped_column(Integer, default=100)
    error: Mapped[str] = mapped_column(Text, default="")
    storage_key: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer_key: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(30), default="formative")
    topic: Mapped[Topic] = relationship()
    attempts: Mapped[list[AssessmentAttempt]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assessment: Mapped[Assessment] = relationship(back_populates="attempts")


class MasteryEvidence(Base):
    __tablename__ = "mastery_evidence"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    source_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewItem(Base):
    __tablename__ = "review_items"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="due")
    # "Quiz me later" from Point & Ask: the mark this review came from and the prompt to re-ask
    spatial_context_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("spatial_contexts.id"), nullable=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[Topic] = relationship()


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30), default="learn")
    status: Mapped[str] = mapped_column(String(30), default="planned")
    planned_minutes: Mapped[int] = mapped_column(Integer, default=30)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    goal: Mapped[Goal] = relationship()
    topic: Mapped[Topic | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(80))
    before_json: Mapped[str] = mapped_column(Text, default="{}")
    after_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelEvent(Base):
    __tablename__ = "model_events"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    task: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    client_version: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SpatialContext(Base):
    __tablename__ = "spatial_contexts"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("goals.id"), index=True, nullable=True)
    # Marks made anywhere (browser extension) may exist before the student has a goal.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    utterance: Mapped[str] = mapped_column(Text)
    marks_json: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), default="study")
    page_url: Mapped[str] = mapped_column(String(2000), default="")
    page_title: Mapped[str] = mapped_column(String(500), default="")
    answer_json: Mapped[str] = mapped_column(Text, default="{}")
    # operator review of low-confidence resolutions: pending | confirmed | corrected | dismissed
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    sensitivity_class: Mapped[str] = mapped_column(String(30), default="private")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    resolution_json: Mapped[str] = mapped_column(Text, default="{}")
    processing_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SpatialUsage(Base):
    """Per-owner daily counters for the zero-install quota and the cost cap."""
    __tablename__ = "spatial_usage"
    __table_args__ = (UniqueConstraint("owner_id", "day", name="uq_spatial_usage_owner_day"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    asks: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class SpatialCorrection(Base):
    __tablename__ = "spatial_corrections"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    context_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spatial_contexts.id"), index=True)
    corrected_marks_json: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LearningPackage(Base):
    __tablename__ = "learning_packages"
    __table_args__ = (UniqueConstraint("slug", "version", name="uq_learning_package_version"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PackageInstall(Base):
    __tablename__ = "package_installs"
    __table_args__ = (UniqueConstraint("user_id", "package_id", name="uq_package_install"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_packages.id"), index=True)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    installed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MonitoringDashboard(Base):
    __tablename__ = "monitoring_dashboards"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    leader_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    access_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MonitoringMember(Base):
    __tablename__ = "monitoring_members"
    __table_args__ = (UniqueConstraint("dashboard_id", "student_user_id", name="uq_monitoring_member"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitoring_dashboards.id"), index=True)
    student_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(default=True)


class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    badge_title: Mapped[str] = mapped_column(String(120), default="")
    target_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    criteria_json: Mapped[str] = mapped_column(Text, default="{}")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="active")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MilestoneShare(Base):
    __tablename__ = "milestone_shares"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    milestone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("milestones.id"), index=True)
    from_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    to_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
