"""add image_file_uuid to image_content

Revision ID: 005_add_image_file_uuid
Revises: 004_rename_image_feedback
Create Date: 2025-11-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_image_file_uuid'
down_revision: Union[str, None] = '004_rename_image_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add image_file_uuid column to image_content table.
    """
    # Check if column exists before adding (for idempotency)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'image_content' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('image_content')]
        if 'image_file_uuid' not in existing_columns:
            op.add_column('image_content', sa.Column('image_file_uuid', sa.String(), nullable=True))
            op.create_index('ix_image_content_image_file_uuid', 'image_content', ['image_file_uuid'], unique=False)
            # Update existing rows to have a default value (optional, but recommended)
            # For now, we'll leave it nullable and let the application handle it


def downgrade() -> None:
    """
    Remove image_file_uuid column from image_content table.
    """
    # Check if column exists before removing
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'image_content' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('image_content')]
        if 'image_file_uuid' in existing_columns:
            op.drop_index('ix_image_content_image_file_uuid', table_name='image_content')
            op.drop_column('image_content', 'image_file_uuid')

