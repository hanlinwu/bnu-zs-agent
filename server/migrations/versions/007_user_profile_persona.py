"""add user profile persona fields

Revision ID: 007_user_profile_persona
Revises: 006_drop_web_search_sites
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa

revision = "007_user_profile_persona"
down_revision = "006_drop_web_search_sites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "users" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("users")}
    if "admission_stages" not in columns:
        op.add_column("users", sa.Column("admission_stages", sa.String(length=100), nullable=True))
    if "identity_type" not in columns:
        op.add_column("users", sa.Column("identity_type", sa.String(length=20), nullable=True))
    if "source_group" not in columns:
        op.add_column("users", sa.Column("source_group", sa.String(length=30), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "users" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("users")}
    if "source_group" in columns:
        op.drop_column("users", "source_group")
    if "identity_type" in columns:
        op.drop_column("users", "identity_type")
    if "admission_stages" in columns:
        op.drop_column("users", "admission_stages")
