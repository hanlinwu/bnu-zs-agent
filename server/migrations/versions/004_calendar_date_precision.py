"""change calendar start_month/end_month to start_date/end_date (keep year)

Revision ID: 004_calendar_date_precision
Revises: 003_knowledge_crawler_depth
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa

revision = "004_calendar_date_precision"
down_revision = "003_knowledge_crawler_depth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "admission_calendar" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("admission_calendar")}

    # Add new date columns
    if "start_date" not in columns:
        op.add_column(
            "admission_calendar",
            sa.Column("start_date", sa.Date(), nullable=True),
        )
    if "end_date" not in columns:
        op.add_column(
            "admission_calendar",
            sa.Column("end_date", sa.Date(), nullable=True),
        )

    # Migrate existing data: convert month + year to date range
    if "start_month" in columns and "year" in columns:
        op.execute(
            sa.text("""
                UPDATE admission_calendar
                SET start_date = make_date(year, start_month, 1),
                    end_date = (make_date(year, end_month, 1) + interval '1 month' - interval '1 day')::date
                WHERE start_date IS NULL
            """)
        )

    # Make columns non-nullable
    op.alter_column("admission_calendar", "start_date", nullable=False)
    op.alter_column("admission_calendar", "end_date", nullable=False)

    # Drop old month columns (keep year)
    if "start_month" in columns:
        op.drop_column("admission_calendar", "start_month")
    if "end_month" in columns:
        op.drop_column("admission_calendar", "end_month")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    if "admission_calendar" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("admission_calendar")}

    # Re-add old columns
    if "start_month" not in columns:
        op.add_column(
            "admission_calendar",
            sa.Column("start_month", sa.Integer(), nullable=True),
        )
    if "end_month" not in columns:
        op.add_column(
            "admission_calendar",
            sa.Column("end_month", sa.Integer(), nullable=True),
        )

    # Migrate data back
    if "start_date" in columns:
        op.execute(
            sa.text("""
                UPDATE admission_calendar
                SET start_month = EXTRACT(MONTH FROM start_date)::int,
                    end_month = EXTRACT(MONTH FROM end_date)::int
                WHERE start_month IS NULL
            """)
        )

    op.alter_column("admission_calendar", "start_month", nullable=False)
    op.alter_column("admission_calendar", "end_month", nullable=False)

    # Drop new columns
    if "start_date" in columns:
        op.drop_column("admission_calendar", "start_date")
    if "end_date" in columns:
        op.drop_column("admission_calendar", "end_date")
