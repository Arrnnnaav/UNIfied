"""model_events.client_version for operator analytics of extension versions in the wild."""

from alembic import op
import sqlalchemy as sa


revision = "0012_client_version"
down_revision = "0011_point_ask_b2c"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("model_events")}
    if "client_version" not in columns:
        op.add_column("model_events", sa.Column("client_version", sa.String(length=40), server_default="", nullable=False))


def downgrade():
    op.drop_column("model_events", "client_version")
