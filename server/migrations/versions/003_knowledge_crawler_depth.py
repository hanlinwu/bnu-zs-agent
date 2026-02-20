"""add max_depth to crawler tasks

Revision ID: 003_knowledge_crawler_depth
Revises: 002_knowledge_crawler_tasks
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa

revision = "003_knowledge_crawler_depth"
down_revision = "002_knowledge_crawler_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "knowledge_crawl_tasks" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("knowledge_crawl_tasks")}
    if "max_depth" not in columns:
        op.add_column(
            "knowledge_crawl_tasks",
            sa.Column("max_depth", sa.Integer(), nullable=False, server_default=sa.text("2")),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "knowledge_crawl_tasks" not in existing_tables:
        return
    columns = {c["name"] for c in inspector.get_columns("knowledge_crawl_tasks")}
    if "max_depth" in columns:
        op.drop_column("knowledge_crawl_tasks", "max_depth")
