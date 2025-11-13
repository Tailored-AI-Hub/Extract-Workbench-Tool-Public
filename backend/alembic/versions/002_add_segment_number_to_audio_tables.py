"""add segment_number to audio tables

Revision ID: 002_add_segment_number
Revises: 001_rename_tables
Create Date: 2025-11-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_segment_number'
down_revision: Union[str, None] = '001_rename_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add segment_number column to audio_file_content, audio_file_feedback, and audio_file_annotations tables.
    """
    # Check if columns exist before adding (for idempotency)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Add segment_number to audio_file_content
    if 'audio_file_content' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('audio_file_content')]
        if 'segment_number' not in existing_columns:
            op.add_column('audio_file_content', sa.Column('segment_number', sa.Integer(), nullable=True))
            op.create_index('ix_audio_file_content_segment_number', 'audio_file_content', ['segment_number'], unique=False)
    
    # Add segment_number to audio_file_feedback
    if 'audio_file_feedback' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('audio_file_feedback')]
        if 'segment_number' not in existing_columns:
            op.add_column('audio_file_feedback', sa.Column('segment_number', sa.Integer(), nullable=True))
            op.create_index('ix_audio_file_feedback_segment_number', 'audio_file_feedback', ['segment_number'], unique=False)
    
    # Add segment_number to audio_file_annotations
    if 'audio_file_annotations' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('audio_file_annotations')]
        if 'segment_number' not in existing_columns:
            op.add_column('audio_file_annotations', sa.Column('segment_number', sa.Integer(), nullable=True))
            op.create_index('ix_audio_file_annotations_segment_number', 'audio_file_annotations', ['segment_number'], unique=False)


def downgrade() -> None:
    """
    Remove segment_number column from audio tables.
    """
    # Remove segment_number from audio_file_annotations
    op.drop_index('ix_audio_file_annotations_segment_number', table_name='audio_file_annotations')
    op.drop_column('audio_file_annotations', 'segment_number')
    
    # Remove segment_number from audio_file_feedback
    op.drop_index('ix_audio_file_feedback_segment_number', table_name='audio_file_feedback')
    op.drop_column('audio_file_feedback', 'segment_number')
    
    # Remove segment_number from audio_file_content
    op.drop_index('ix_audio_file_content_segment_number', table_name='audio_file_content')
    op.drop_column('audio_file_content', 'segment_number')

