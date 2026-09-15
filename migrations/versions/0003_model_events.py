"""Add aggregate-safe model runtime telemetry."""

from alembic import op
from app.core.models import ModelEvent


revision = "0003_model_events"
down_revision = "0002_spatial_corrections"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    ModelEvent.__table__.create(bind, checkfirst=True)


def downgrade():
    op.drop_index("ix_model_events_created_at", table_name="model_events")
    op.drop_index("ix_model_events_status", table_name="model_events")
    op.drop_index("ix_model_events_task", table_name="model_events")
    op.drop_table("model_events")
