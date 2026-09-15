"""Add explicit curriculum prerequisite edges."""

from alembic import op

from app.core.models import TopicDependency


revision = "0005_topic_dependencies"
down_revision = "0004_learner_profiles"
branch_labels = None
depends_on = None


def upgrade():
    TopicDependency.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    TopicDependency.__table__.drop(op.get_bind(), checkfirst=True)
