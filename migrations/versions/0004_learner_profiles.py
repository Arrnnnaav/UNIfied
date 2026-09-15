"""Add first-class learner onboarding profile."""

from alembic import op

from app.core.models import LearnerProfile


revision = "0004_learner_profiles"
down_revision = "0003_model_events"
branch_labels = None
depends_on = None


def upgrade():
    LearnerProfile.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    LearnerProfile.__table__.drop(op.get_bind(), checkfirst=True)
