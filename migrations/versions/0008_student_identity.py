"""Add student identity, college context, and coding-profile fields."""

from alembic import op
import sqlalchemy as sa


revision = "0008_student_identity"
down_revision = "0007_learning_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("student_id", sa.String(length=30), nullable=True))
    op.create_index("ix_users_student_id", "users", ["student_id"], unique=True)
    op.add_column("learner_profiles", sa.Column("college_name", sa.String(length=200), server_default="", nullable=False))
    op.add_column("learner_profiles", sa.Column("college_year", sa.String(length=40), server_default="", nullable=False))
    op.add_column("learner_profiles", sa.Column("branch", sa.String(length=120), server_default="", nullable=False))
    op.add_column("learner_profiles", sa.Column("college_id", sa.String(length=120), server_default="", nullable=False))
    op.add_column("learner_profiles", sa.Column("coding_profiles_json", sa.Text(), server_default="{}", nullable=False))
    # Existing rows receive stable, non-sensitive IDs before the model's
    # application-level generator is used for future registrations.
    bind = op.get_bind()
    rows = bind.execute(sa.text("select id from users where student_id is null")).fetchall()
    import uuid
    for row in rows:
        bind.execute(sa.text("update users set student_id=:student_id where id=:id"), {"student_id": f"STU-{uuid.uuid4().hex[:10].upper()}", "id": row[0]})


def downgrade():
    op.drop_index("ix_users_student_id", table_name="users")
    op.drop_column("users", "student_id")
    for name in ("coding_profiles_json", "college_id", "branch", "college_year", "college_name"):
        op.drop_column("learner_profiles", name)
