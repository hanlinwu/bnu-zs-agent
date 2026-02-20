"""add knowledge crawler task table

Revision ID: 002_knowledge_crawler_tasks
Revises: 001_media_review
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002_knowledge_crawler_tasks"
down_revision = "001_media_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "knowledge_crawl_tasks" not in existing_tables:
        op.create_table(
            "knowledge_crawl_tasks",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=False),
            sa.Column("start_url", sa.String(length=1000), nullable=False),
            sa.Column("max_pages", sa.Integer(), nullable=False, server_default=sa.text("2")),
            sa.Column("same_domain_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("total_pages", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("success_pages", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("failed_pages", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("current_url", sa.String(length=1000), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("result_document_ids", JSONB(), nullable=True),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("admin_users.id"), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
        op.create_index("ix_knowledge_crawl_tasks_kb_id", "knowledge_crawl_tasks", ["kb_id"])
        op.create_index("ix_knowledge_crawl_tasks_status", "knowledge_crawl_tasks", ["status"])
        op.create_index("ix_knowledge_crawl_tasks_created_at", "knowledge_crawl_tasks", ["created_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "knowledge_crawl_tasks" in existing_tables:
        op.drop_index("ix_knowledge_crawl_tasks_created_at", table_name="knowledge_crawl_tasks")
        op.drop_index("ix_knowledge_crawl_tasks_status", table_name="knowledge_crawl_tasks")
        op.drop_index("ix_knowledge_crawl_tasks_kb_id", table_name="knowledge_crawl_tasks")
        op.drop_table("knowledge_crawl_tasks")
