"""add media review columns

Revision ID: 001_media_review
Revises:
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001_media_review"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to media_resources (IF NOT EXISTS for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "media_resources" in existing_tables:
        existing = {c["name"] for c in inspector.get_columns("media_resources")}

        if "file_size" not in existing:
            op.add_column("media_resources", sa.Column("file_size", sa.Integer(), nullable=True))
        if "status" not in existing:
            op.add_column("media_resources", sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")))
        if "current_step" not in existing:
            op.add_column("media_resources", sa.Column("current_step", sa.Integer(), nullable=False, server_default=sa.text("0")))
        if "reviewed_by" not in existing:
            op.add_column("media_resources", sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("admin_users.id"), nullable=True))
        if "review_note" not in existing:
            op.add_column("media_resources", sa.Column("review_note", sa.Text(), nullable=True))

        # Migrate existing data: is_approved=True → status='approved'
        op.execute("UPDATE media_resources SET status = 'approved' WHERE is_approved = true AND status = 'pending'")

    # Add current_step to knowledge_documents if missing
    if "knowledge_documents" in existing_tables:
        kd_existing = {c["name"] for c in inspector.get_columns("knowledge_documents")}
        if "current_step" not in kd_existing:
            op.add_column("knowledge_documents", sa.Column("current_step", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    op.drop_column("media_resources", "review_note")
    op.drop_column("media_resources", "reviewed_by")
    op.drop_column("media_resources", "current_step")
    op.drop_column("media_resources", "status")
    op.drop_column("media_resources", "file_size")
