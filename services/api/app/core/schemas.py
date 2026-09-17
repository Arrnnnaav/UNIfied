from datetime import date
from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    goal_type: str = "skill"
    target_date: date | None = None
    weekly_hours: int = Field(default=8, ge=1, le=80)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=200)
    college_name: str = Field(default="", max_length=200)
    college_year: str = Field(default="", max_length=40)
    branch: str = Field(default="", max_length=120)
    college_id: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


class LearnerProfileUpdate(BaseModel):
    education_stage: str = Field(default="other", max_length=40)
    graduation_year: int | None = Field(default=None, ge=1950, le=2200)
    current_skill_level: str = Field(default="beginner", max_length=40)
    known_skills: list[str] = Field(default_factory=list, max_length=50)
    learning_modes: list[str] = Field(default_factory=lambda: ["mixed"], max_length=10)
    preferred_pace: str = Field(default="steady", max_length=30)
    constraints: str = Field(default="", max_length=2000)
    college_name: str = Field(default="", max_length=200)
    college_year: str = Field(default="", max_length=40)
    branch: str = Field(default="", max_length=120)
    college_id: str = Field(default="", max_length=120)
    coding_profiles: dict[str, str] = Field(default_factory=dict, max_length=10)


class TopicCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    phase_id: str
    description: str = ""
    estimated_minutes: int = Field(default=30, ge=5, le=600)


class TopicUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    difficulty: str | None = Field(default=None, max_length=30)
    estimated_minutes: int | None = Field(default=None, ge=5, le=600)


class DependencyCreate(BaseModel):
    prerequisite_topic_id: str
    relation: str = Field(default="prerequisite_of", max_length=40)


class ObjectiveCreate(BaseModel):
    text: str = Field(min_length=3, max_length=500)


class ProgressUpdate(BaseModel):
    progress: float = Field(ge=0, le=1)
    mastery: float | None = Field(default=None, ge=0, le=1)


class ResourceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    url: str | None = None
    topic_id: str | None = None
    content: str = ""
    source_type: str = "link"


class SpatialContextCreate(BaseModel):
    goal_id: str
    utterance: str = Field(min_length=1, max_length=2000)
    marks: list[dict]
    canvas: dict[str, float] | None = None
    source: str = "study"
    surface: str = "unknown"
    anchors: list[dict] = Field(default_factory=list)
    crop_ref: dict | None = None
    privacy_policy: str = "local_or_redacted"
    image_data: str | None = Field(default=None, max_length=6_000_000)


class SpatialPage(BaseModel):
    url: str = Field(default="", max_length=2000)
    title: str = Field(default="", max_length=500)
    surface: str = Field(default="web", max_length=30)


class SpatialAsk(BaseModel):
    """Point & Ask from anywhere: marks over any page/PDF plus a question."""
    question: str = Field(min_length=1, max_length=2000)
    marks: list[dict]
    canvas: dict[str, float] | None = None
    anchors: list[dict] = Field(default_factory=list)
    page: SpatialPage = Field(default_factory=SpatialPage)
    goal_id: str | None = None
    context_id: str | None = None
    source: str = Field(default="extension", max_length=30)
    privacy_policy: str = Field(default="crop_only", max_length=30)
    image_data: str | None = Field(default=None, max_length=8_000_000)
    protocol_version: int = 2
    client_version: str | None = Field(default=None, max_length=40)
    provider: str | None = Field(default=None, max_length=30)
    research: bool = False
    level: str | None = Field(default=None, max_length=10)


class SpatialCorrectionCreate(BaseModel):
    marks: list[dict]
    note: str = Field(default="", max_length=1000)
    canvas: dict[str, float] | None = None


class AssessmentAttemptCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


class TutorAsk(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    goal_id: str | None = None
    topic_id: str | None = None
    spatial_context_id: str | None = None


class LearningSessionCreate(BaseModel):
    goal_id: str | None = None
    topic_id: str | None = None
    kind: str = Field(default="learn", max_length=30)
    planned_minutes: int = Field(default=30, ge=5, le=600)


class LearningSessionUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=30)
    actual_minutes: int | None = Field(default=None, ge=0, le=1440)
    notes: str | None = Field(default=None, max_length=4000)


class PackageCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(default="", max_length=4000)
    version: str = Field(default="1.0.0", max_length=30)
    manifest: dict = Field(default_factory=dict)
    status: str = Field(default="draft", max_length=30)


class PackageInstallCreate(BaseModel):
    package_id: str
    goal_title: str | None = Field(default=None, max_length=200)


class MonitoringDashboardCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    leader_student_id: str


class MonitoringMemberCreate(BaseModel):
    student_id: str


class MilestoneCreate(BaseModel):
    goal_id: str | None = None
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=1000)
    badge_title: str = Field(default="", max_length=120)
    target_date: date | None = None
    criteria: dict = Field(default_factory=dict)


class MilestoneShareCreate(BaseModel):
    recipient_student_id: str
    message: str = Field(default="", max_length=500)
