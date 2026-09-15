"""Initial unified platform schema."""

from alembic import op

from app.core.models import Base


revision = "0001_initial_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind)


def downgrade():
    Base.metadata.drop_all(op.get_bind())
