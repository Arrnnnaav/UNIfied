"""Spatial Context anywhere: marks owned directly by a student, page metadata, stored answers."""

from alembic import op
import sqlalchemy as sa

from app.core.models import GUID


revision = "0010_spatial_anywhere"
down_revision = "0009_packages_community"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("spatial_contexts")}
    if "answer_json" in existing:
        # Fresh databases are created from the current models in 0001; nothing to change.
        return
    with op.batch_alter_table("spatial_contexts") as batch:
        batch.alter_column("goal_id", existing_type=GUID(), nullable=True)
        batch.add_column(sa.Column("owner_id", GUID(), sa.ForeignKey("users.id", name="fk_spatial_contexts_owner_id_users"), nullable=True))
        batch.add_column(sa.Column("page_url", sa.String(length=2000), server_default="", nullable=False))
        batch.add_column(sa.Column("page_title", sa.String(length=500), server_default="", nullable=False))
        batch.add_column(sa.Column("answer_json", sa.Text(), server_default="{}", nullable=False))
    op.create_index("ix_spatial_contexts_owner_id", "spatial_contexts", ["owner_id"])
    # Existing in-app marks belong to the goal owner.
    op.execute(sa.text("update spatial_contexts set owner_id = (select owner_id from goals where goals.id = spatial_contexts.goal_id) where owner_id is null"))


def downgrade():
    op.execute(sa.text("delete from spatial_contexts where goal_id is null"))
    op.drop_index("ix_spatial_contexts_owner_id", table_name="spatial_contexts")
    with op.batch_alter_table("spatial_contexts") as batch:
        for name in ("answer_json", "page_title", "page_url", "owner_id"):
            batch.drop_column(name)
        batch.alter_column("goal_id", existing_type=GUID(), nullable=False)
