"""rename image_uuid to image_file_uuid in image_feedback

Revision ID: 004_rename_image_feedback
Revises: 002_add_segment_number
Create Date: 2025-11-11 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_rename_image_feedback'
down_revision: Union[str, None] = '002_add_segment_number'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Rename image_uuid column to image_file_uuid in image_feedback table.
    """
    # Check if column exists before renaming
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'image_feedback' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('image_feedback')]
        if 'image_uuid' in existing_columns and 'image_file_uuid' not in existing_columns:
            op.alter_column('image_feedback', 'image_uuid', new_column_name='image_file_uuid')


def downgrade() -> None:
    """
    Rename image_file_uuid column back to image_uuid in image_feedback table.
    """
    # Check if column exists before renaming
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'image_feedback' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('image_feedback')]
        if 'image_file_uuid' in existing_columns and 'image_uuid' not in existing_columns:
            op.alter_column('image_feedback', 'image_file_uuid', new_column_name='image_uuid')

