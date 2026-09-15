"""Persist semantic concepts and curriculum alignment provenance."""

from alembic import op

from app.core.models import SemanticConcept, TopicConceptAlignment


revision = "0006_semantic_alignment"
down_revision = "0005_topic_dependencies"
branch_labels = None
depends_on = None


def upgrade():
    SemanticConcept.__table__.create(op.get_bind(), checkfirst=True)
    TopicConceptAlignment.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    TopicConceptAlignment.__table__.drop(op.get_bind(), checkfirst=True)
    SemanticConcept.__table__.drop(op.get_bind(), checkfirst=True)
