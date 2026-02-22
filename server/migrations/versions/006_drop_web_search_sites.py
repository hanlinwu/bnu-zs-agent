"""Drop web_search_sites table — replaced by Tavily config in system_configs.

Revision ID: 006_drop_web_search_sites
Revises: 005_web_search_sites
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "006_drop_web_search_sites"
down_revision = "005_web_search_sites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "web_search_sites" in set(inspector.get_table_names()):
        op.drop_index("ix_web_search_sites_enabled", table_name="web_search_sites")
        op.drop_index("ix_web_search_sites_domain", table_name="web_search_sites")
        op.drop_table("web_search_sites")


def downgrade() -> None:
    op.create_table(
        "web_search_sites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain", sa.String(500), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_url", sa.String(1000), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("same_domain_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("crawl_frequency_minutes", sa.Integer(), nullable=False, server_default=sa.text("1440")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remote_site_id", sa.String(100), nullable=True),
        sa.Column("last_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_crawl_status", sa.String(20), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_web_search_sites_domain", "web_search_sites", ["domain"])
    op.create_index("ix_web_search_sites_enabled", "web_search_sites", ["enabled"])
