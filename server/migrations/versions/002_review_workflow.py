"""add review workflow tables

Revision ID: 002_review_workflow
Revises: 001_media_review
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002_review_workflow"
down_revision = "001_media_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "review_workflows" not in existing_tables:
        op.create_table(
            "review_workflows",
            sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("code", sa.String(50), unique=True, nullable=False),
            sa.Column("steps", JSONB, nullable=False),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )

    if "resource_workflow_bindings" not in existing_tables:
        op.create_table(
            "resource_workflow_bindings",
            sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
            sa.Column("resource_type", sa.String(50), unique=True, nullable=False),
            sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("review_workflows.id"), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )

    if "review_records" not in existing_tables:
        op.create_table(
            "review_records",
            sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
            sa.Column("resource_type", sa.String(50), nullable=False),
            sa.Column("resource_id", UUID(as_uuid=True), nullable=False),
            sa.Column("step", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("reviewer_id", UUID(as_uuid=True), sa.ForeignKey("admin_users.id"), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )

    if "review_records" in set(inspector.get_table_names()):
        indexes = {idx["name"] for idx in inspector.get_indexes("review_records")}
        if "ix_review_records_resource" not in indexes:
            op.create_index("ix_review_records_resource", "review_records", ["resource_type", "resource_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "review_records" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("review_records")}
        if "ix_review_records_resource" in indexes:
            op.drop_index("ix_review_records_resource", table_name="review_records")
        op.drop_table("review_records")

    existing_tables = set(sa.inspect(conn).get_table_names())
    if "resource_workflow_bindings" in existing_tables:
        op.drop_table("resource_workflow_bindings")

    existing_tables = set(sa.inspect(conn).get_table_names())
    if "review_workflows" in existing_tables:
        op.drop_table("review_workflows")
