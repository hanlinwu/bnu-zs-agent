"""add web_search_sites table

Revision ID: 005_web_search_sites
Revises: 004_calendar_date_precision
Create Date: 2026-02-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005_web_search_sites"
down_revision = "004_calendar_date_precision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "web_search_sites" not in existing_tables:
        op.create_table(
            "web_search_sites",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("domain", sa.String(length=500), nullable=False, unique=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("start_url", sa.String(length=1000), nullable=False),
            sa.Column("max_depth", sa.Integer(), nullable=False, server_default=sa.text("3")),
            sa.Column("max_pages", sa.Integer(), nullable=False, server_default=sa.text("100")),
            sa.Column("same_domain_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("crawl_frequency_minutes", sa.Integer(), nullable=False, server_default=sa.text("1440")),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("remote_site_id", sa.String(length=100), nullable=True),
            sa.Column("last_crawl_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_crawl_status", sa.String(length=20), nullable=True),
            sa.Column("created_by", UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
        op.create_index("ix_web_search_sites_domain", "web_search_sites", ["domain"])
        op.create_index("ix_web_search_sites_enabled", "web_search_sites", ["enabled"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "web_search_sites" in existing_tables:
        op.drop_index("ix_web_search_sites_enabled", table_name="web_search_sites")
        op.drop_index("ix_web_search_sites_domain", table_name="web_search_sites")
        op.drop_table("web_search_sites")
