"""Persist adaptive study sessions and their completion evidence."""

from alembic import op

from app.core.models import LearningSession


revision = "0007_learning_sessions"
down_revision = "0006_semantic_alignment"
branch_labels = None
depends_on = None


def upgrade():
    LearningSession.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    LearningSession.__table__.drop(op.get_bind(), checkfirst=True)
