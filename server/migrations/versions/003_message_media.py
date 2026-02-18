"""Add message_media association table

Revision ID: 003
Revises: 002_review_workflow
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002_review_workflow'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'message_media' not in existing_tables:
        op.create_table(
            'message_media',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
            sa.Column('media_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('media_resources.id', ondelete='CASCADE'), nullable=False),
            sa.Column('slot_key', sa.String(50), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        )

    indexes = {idx['name'] for idx in inspector.get_indexes('message_media')} if 'message_media' in set(inspector.get_table_names()) else set()
    if 'idx_message_media_message' not in indexes:
        op.create_index('idx_message_media_message', 'message_media', ['message_id'])
    if 'idx_message_media_media' not in indexes:
        op.create_index('idx_message_media_media', 'message_media', ['media_id'])


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'message_media' in set(inspector.get_table_names()):
        indexes = {idx['name'] for idx in inspector.get_indexes('message_media')}
        if 'idx_message_media_media' in indexes:
            op.drop_index('idx_message_media_media', table_name='message_media')
        if 'idx_message_media_message' in indexes:
            op.drop_index('idx_message_media_message', table_name='message_media')
        op.drop_table('message_media')
