"""baseline schema (merged migrations)

Revision ID: 001_media_review
Revises:
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base
import app.models  # noqa: F401

revision = "001_media_review"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Baseline bootstrap: for fresh databases, create all current model tables first.
    # Subsequent migration steps below remain idempotent and act as compatibility patches.
    Base.metadata.create_all(bind=conn)

    # Add new columns to media_resources (IF NOT EXISTS for idempotency)
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
        if "kb_id" not in kd_existing:
            op.add_column("knowledge_documents", sa.Column("kb_id", UUID(as_uuid=True), nullable=True))
            if "knowledge_bases" in existing_tables:
                fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("knowledge_documents")}
                if "fk_knowledge_documents_kb_id_knowledge_bases" not in fk_names:
                    op.create_foreign_key(
                        "fk_knowledge_documents_kb_id_knowledge_bases",
                        "knowledge_documents",
                        "knowledge_bases",
                        ["kb_id"],
                        ["id"],
                    )

    # Ensure review workflow related compatibility
    existing_tables = set(sa.inspect(conn).get_table_names())
    if "review_workflows" in existing_tables:
        rw_existing = {c["name"] for c in sa.inspect(conn).get_columns("review_workflows")}
        if "definition" not in rw_existing:
            op.add_column("review_workflows", sa.Column("definition", JSONB(), nullable=True))

    if "review_records" in existing_tables:
        rr_existing = {c["name"] for c in sa.inspect(conn).get_columns("review_records")}
        if "step" in rr_existing:
            op.execute("ALTER TABLE review_records ALTER COLUMN step DROP NOT NULL")
            op.execute("ALTER TABLE review_records ALTER COLUMN step SET DEFAULT 0")

        rr_indexes = {idx["name"] for idx in sa.inspect(conn).get_indexes("review_records")}
        if "ix_review_records_resource" not in rr_indexes:
            op.create_index("ix_review_records_resource", "review_records", ["resource_type", "resource_id"])

    # Ensure message_media indexes
    existing_tables = set(sa.inspect(conn).get_table_names())
    if "message_media" in existing_tables:
        mm_indexes = {idx["name"] for idx in sa.inspect(conn).get_indexes("message_media")}
        if "idx_message_media_message" not in mm_indexes:
            op.create_index("idx_message_media_message", "message_media", ["message_id"])
        if "idx_message_media_media" not in mm_indexes:
            op.create_index("idx_message_media_media", "message_media", ["media_id"])

    # Ensure sensitive and calendar extra columns
    if "sensitive_word_groups" in existing_tables:
        swg_existing = {c["name"] for c in sa.inspect(conn).get_columns("sensitive_word_groups")}
        if "level" not in swg_existing:
            op.add_column("sensitive_word_groups", sa.Column("level", sa.String(10), nullable=False, server_default=sa.text("'block'")))
        if "word_list" not in swg_existing:
            op.add_column("sensitive_word_groups", sa.Column("word_list", sa.Text(), nullable=True))

    if "admission_calendar" in existing_tables:
        cal_existing = {c["name"] for c in sa.inspect(conn).get_columns("admission_calendar")}
        if "additional_prompt" not in cal_existing:
            op.add_column("admission_calendar", sa.Column("additional_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    # Baseline migration is intentionally non-destructive on downgrade.
    # Use backup/restore for full rollback in production.
    pass
