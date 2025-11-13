"""fix image_content foreign key to reference image_file_extraction_jobs

Revision ID: 006_fix_image_content_fk
Revises: 005_add_image_file_uuid
Create Date: 2025-11-11 11:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_fix_image_content_fk'
down_revision: Union[str, None] = '005_add_image_file_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix the foreign key constraint on image_content.extraction_job_uuid to reference
    image_file_extraction_jobs instead of image_extraction_jobs.
    """
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    
    # Only proceed if image_content table exists
    if 'image_content' not in existing_tables:
        # Table doesn't exist yet - skip this migration step
        # This can happen on fresh databases where tables haven't been created yet
        return
    
    # First, clean up orphaned rows that reference jobs not in image_file_extraction_jobs
    # Only if image_file_extraction_jobs table exists
    if 'image_file_extraction_jobs' in existing_tables:
        try:
            op.execute("""
                DELETE FROM image_content 
                WHERE extraction_job_uuid NOT IN (
                    SELECT uuid FROM image_file_extraction_jobs
                )
            """)
        except Exception:
            # If deletion fails (e.g., no rows to delete), continue
            pass
    
    # Drop the old foreign key constraint if it exists
    try:
        # Check if constraint exists before dropping
        foreign_keys = inspector.get_foreign_keys('image_content')
        constraint_names = [fk['name'] for fk in foreign_keys]
        
        if 'image_content_extraction_job_uuid_fkey' in constraint_names:
            op.drop_constraint(
                'image_content_extraction_job_uuid_fkey',
                'image_content',
                type_='foreignkey'
            )
    except Exception:
        # If constraint doesn't exist or drop fails, continue
        pass
    
    # Add the correct foreign key constraint only if target table exists
    if 'image_file_extraction_jobs' in existing_tables:
        try:
            op.create_foreign_key(
                'image_content_extraction_job_uuid_fkey',
                'image_content',
                'image_file_extraction_jobs',
                ['extraction_job_uuid'],
                ['uuid']
            )
        except Exception:
            # If constraint already exists or creation fails, skip
            pass


def downgrade() -> None:
    """
    Revert the foreign key constraint back to image_extraction_jobs.
    """
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    
    # Only proceed if image_content table exists
    if 'image_content' not in existing_tables:
        return
    
    # Drop the new foreign key constraint if it exists
    try:
        foreign_keys = inspector.get_foreign_keys('image_content')
        constraint_names = [fk['name'] for fk in foreign_keys]
        
        if 'image_content_extraction_job_uuid_fkey' in constraint_names:
            op.drop_constraint(
                'image_content_extraction_job_uuid_fkey',
                'image_content',
                type_='foreignkey'
            )
    except Exception:
        pass
    
    # Re-add the old foreign key constraint (if image_extraction_jobs table still exists)
    if 'image_extraction_jobs' in existing_tables:
        try:
            op.create_foreign_key(
                'image_content_extraction_job_uuid_fkey',
                'image_content',
                'image_extraction_jobs',
                ['extraction_job_uuid'],
                ['uuid']
            )
        except Exception:
            # If the old table doesn't exist or constraint creation fails, skip
            pass

