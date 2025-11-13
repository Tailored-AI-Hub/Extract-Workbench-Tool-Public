"""fix image_annotations foreign key to reference image_files

Revision ID: 007_fix_image_annotations_fk
Revises: 006_fix_image_content_fk
Create Date: 2025-11-11 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_fix_image_annotations_fk'
down_revision: Union[str, None] = '006_fix_image_content_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix the foreign key constraints on image_annotations and image_feedback.image_file_uuid 
    to reference image_files instead of images.
    """
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    
    # Fix image_annotations foreign keys (only if table exists)
    if 'image_annotations' in existing_tables:
        # Fix image_file_uuid foreign key
        try:
            foreign_keys = inspector.get_foreign_keys('image_annotations')
            constraint_names = [fk['name'] for fk in foreign_keys]
            
            if 'image_annotations_image_uuid_fkey' in constraint_names:
                op.drop_constraint(
                    'image_annotations_image_uuid_fkey',
                    'image_annotations',
                    type_='foreignkey'
                )
        except Exception:
            pass
        
        # Add new foreign key if target table exists
        if 'image_files' in existing_tables:
            try:
                op.create_foreign_key(
                    'image_annotations_image_uuid_fkey',
                    'image_annotations',
                    'image_files',
                    ['image_file_uuid'],
                    ['uuid']
                )
            except Exception:
                pass
        
        # Fix extraction_job_uuid foreign key
        try:
            foreign_keys = inspector.get_foreign_keys('image_annotations')
            constraint_names = [fk['name'] for fk in foreign_keys]
            
            if 'image_annotations_extraction_job_uuid_fkey' in constraint_names:
                op.drop_constraint(
                    'image_annotations_extraction_job_uuid_fkey',
                    'image_annotations',
                    type_='foreignkey'
                )
        except Exception:
            pass
        
        # Add new foreign key if target table exists
        if 'image_file_extraction_jobs' in existing_tables:
            try:
                op.create_foreign_key(
                    'image_annotations_extraction_job_uuid_fkey',
                    'image_annotations',
                    'image_file_extraction_jobs',
                    ['extraction_job_uuid'],
                    ['uuid']
                )
            except Exception:
                pass
    
    # Fix image_feedback foreign key (only if table exists)
    if 'image_feedback' in existing_tables:
        try:
            foreign_keys = inspector.get_foreign_keys('image_feedback')
            constraint_names = [fk['name'] for fk in foreign_keys]
            
            if 'image_feedback_image_uuid_fkey' in constraint_names:
                op.drop_constraint(
                    'image_feedback_image_uuid_fkey',
                    'image_feedback',
                    type_='foreignkey'
                )
        except Exception:
            pass
        
        # Add new foreign key if target table exists
        if 'image_files' in existing_tables:
            try:
                op.create_foreign_key(
                    'image_feedback_image_uuid_fkey',
                    'image_feedback',
                    'image_files',
                    ['image_file_uuid'],
                    ['uuid']
                )
            except Exception:
                pass


def downgrade() -> None:
    """
    Revert the foreign key constraints back to images.
    """
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    
    # Revert image_annotations foreign keys (only if table exists)
    if 'image_annotations' in existing_tables:
        try:
            foreign_keys = inspector.get_foreign_keys('image_annotations')
            constraint_names = [fk['name'] for fk in foreign_keys]
            
            if 'image_annotations_image_uuid_fkey' in constraint_names:
                op.drop_constraint(
                    'image_annotations_image_uuid_fkey',
                    'image_annotations',
                    type_='foreignkey'
                )
        except Exception:
            pass
        
        # Re-add old foreign key if old table exists
        if 'images' in existing_tables:
            try:
                op.create_foreign_key(
                    'image_annotations_image_uuid_fkey',
                    'image_annotations',
                    'images',
                    ['image_file_uuid'],
                    ['uuid']
                )
            except Exception:
                pass
        
        try:
            foreign_keys = inspector.get_foreign_keys('image_annotations')
            constraint_names = [fk['name'] for fk in foreign_keys]
            
            if 'image_annotations_extraction_job_uuid_fkey' in constraint_names:
                op.drop_constraint(
                    'image_annotations_extraction_job_uuid_fkey',
                    'image_annotations',
                    type_='foreignkey'
                )
        except Exception:
            pass
    
    # Revert image_feedback foreign key (only if table exists)
    if 'image_feedback' in existing_tables:
        try:
            foreign_keys = inspector.get_foreign_keys('image_feedback')
            constraint_names = [fk['name'] for fk in foreign_keys]
            
            if 'image_feedback_image_uuid_fkey' in constraint_names:
                op.drop_constraint(
                    'image_feedback_image_uuid_fkey',
                    'image_feedback',
                    type_='foreignkey'
                )
        except Exception:
            pass
        
        # Re-add old foreign key if old table exists
        if 'images' in existing_tables:
            try:
                op.create_foreign_key(
                    'image_feedback_image_uuid_fkey',
                    'image_feedback',
                    'images',
                    ['image_file_uuid'],
                    ['uuid']
                )
            except Exception:
                pass

