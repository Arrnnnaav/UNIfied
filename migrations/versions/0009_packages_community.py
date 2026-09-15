"""Add fixed learning packages, monitoring groups, milestones, and shares."""

from alembic import op

from app.core.models import LearningPackage, Milestone, MilestoneShare, MonitoringDashboard, MonitoringMember, PackageInstall


revision = "0009_packages_community"
down_revision = "0008_student_identity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Reuse the application's GUID type so SQLite smoke databases and
    # PostgreSQL foreign keys have matching column types.
    for model in (LearningPackage, PackageInstall, MonitoringDashboard, MonitoringMember, Milestone, MilestoneShare):
        model.__table__.create(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    for model in (MilestoneShare, Milestone, MonitoringMember, MonitoringDashboard, PackageInstall, LearningPackage):
        model.__table__.drop(bind, checkfirst=True)
