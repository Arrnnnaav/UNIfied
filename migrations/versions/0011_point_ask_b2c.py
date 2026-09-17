"""Point & Ask B2C: cost telemetry, operator review status, quiz-me-later links, daily usage counters."""

from alembic import op
import sqlalchemy as sa

from app.core.models import GUID, SpatialUsage


revision = "0011_point_ask_b2c"
down_revision = "0010_spatial_anywhere"
branch_labels = None
depends_on = None


def _columns(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    if "cost_usd" not in _columns(bind, "model_events"):
        op.add_column("model_events", sa.Column("cost_usd", sa.Float(), server_default="0", nullable=False))
    if "review_status" not in _columns(bind, "spatial_contexts"):
        op.add_column("spatial_contexts", sa.Column("review_status", sa.String(length=20), server_default="pending", nullable=False))
    if "spatial_context_id" not in _columns(bind, "review_items"):
        with op.batch_alter_table("review_items") as batch:
            batch.add_column(sa.Column("spatial_context_id", GUID(), sa.ForeignKey("spatial_contexts.id", name="fk_review_items_spatial_context"), nullable=True))
            batch.add_column(sa.Column("prompt", sa.Text(), server_default="", nullable=False))
        op.create_index("ix_review_items_spatial_context_id", "review_items", ["spatial_context_id"])
    SpatialUsage.__table__.create(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    SpatialUsage.__table__.drop(bind, checkfirst=True)
    op.drop_index("ix_review_items_spatial_context_id", table_name="review_items")
    with op.batch_alter_table("review_items") as batch:
        batch.drop_column("prompt")
        batch.drop_column("spatial_context_id")
    op.drop_column("spatial_contexts", "review_status")
    op.drop_column("model_events", "cost_usd")
