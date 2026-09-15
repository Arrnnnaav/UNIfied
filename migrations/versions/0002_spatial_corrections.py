"""Persist student corrections to spatial interpretations."""

from alembic import op

from app.core.models import SpatialCorrection


revision = "0002_spatial_corrections"
down_revision = "0001_initial_platform"
branch_labels = None
depends_on = None


def upgrade():
    SpatialCorrection.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    SpatialCorrection.__table__.drop(op.get_bind(), checkfirst=True)
