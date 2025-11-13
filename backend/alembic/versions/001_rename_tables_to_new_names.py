"""rename tables to new names

Revision ID: 001_rename_tables
Revises: 
Create Date: 2025-11-11 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_rename_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Rename old table names to new table names to match the updated model definitions.
    Also handles PostgreSQL type conflicts by checking if tables exist before renaming.
    """
    # Check if tables exist before renaming
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    
    # PDF/Document tables
    if 'projects' in existing_tables and 'pdf_projects' not in existing_tables:
        op.execute('ALTER TABLE projects RENAME TO pdf_projects')
    if 'documents' in existing_tables and 'pdf_files' not in existing_tables:
        op.execute('ALTER TABLE documents RENAME TO pdf_files')
    if 'document_extraction_jobs' in existing_tables and 'pdf_file_extraction_jobs' not in existing_tables:
        op.execute('ALTER TABLE document_extraction_jobs RENAME TO pdf_file_extraction_jobs')
    if 'document_page_content' in existing_tables and 'pdf_file_page_content' not in existing_tables:
        op.execute('ALTER TABLE document_page_content RENAME TO pdf_file_page_content')
    if 'document_page_feedback' in existing_tables and 'pdf_file_page_feedback' not in existing_tables:
        op.execute('ALTER TABLE document_page_feedback RENAME TO pdf_file_page_feedback')
    if 'annotations' in existing_tables and 'pdf_file_annotations' not in existing_tables:
        op.execute('ALTER TABLE annotations RENAME TO pdf_file_annotations')
    
    # Audio tables
    if 'audios' in existing_tables and 'audio_files' not in existing_tables:
        op.execute('ALTER TABLE audios RENAME TO audio_files')
    if 'audio_extraction_jobs' in existing_tables and 'audio_file_extraction_jobs' not in existing_tables:
        op.execute('ALTER TABLE audio_extraction_jobs RENAME TO audio_file_extraction_jobs')
    if 'audio_segment_content' in existing_tables and 'audio_file_content' not in existing_tables:
        op.execute('ALTER TABLE audio_segment_content RENAME TO audio_file_content')
    if 'audio_segment_feedback' in existing_tables and 'audio_file_feedback' not in existing_tables:
        op.execute('ALTER TABLE audio_segment_feedback RENAME TO audio_file_feedback')
    if 'audio_annotations' in existing_tables and 'audio_file_annotations' not in existing_tables:
        op.execute('ALTER TABLE audio_annotations RENAME TO audio_file_annotations')
    
    # Image tables
    if 'images' in existing_tables and 'image_files' not in existing_tables:
        op.execute('ALTER TABLE images RENAME TO image_files')
    if 'image_extraction_jobs' in existing_tables and 'image_file_extraction_jobs' not in existing_tables:
        op.execute('ALTER TABLE image_extraction_jobs RENAME TO image_file_extraction_jobs')
    
    # Note: image_content, image_feedback, image_annotations don't need renaming
    # as they already match the model names


def downgrade() -> None:
    """
    Revert table names back to old names.
    """
    # Check if tables exist before renaming
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    
    # PDF/Document tables
    if 'pdf_projects' in existing_tables and 'projects' not in existing_tables:
        op.execute('ALTER TABLE pdf_projects RENAME TO projects')
    if 'pdf_files' in existing_tables and 'documents' not in existing_tables:
        op.execute('ALTER TABLE pdf_files RENAME TO documents')
    if 'pdf_file_extraction_jobs' in existing_tables and 'document_extraction_jobs' not in existing_tables:
        op.execute('ALTER TABLE pdf_file_extraction_jobs RENAME TO document_extraction_jobs')
    if 'pdf_file_page_content' in existing_tables and 'document_page_content' not in existing_tables:
        op.execute('ALTER TABLE pdf_file_page_content RENAME TO document_page_content')
    if 'pdf_file_page_feedback' in existing_tables and 'document_page_feedback' not in existing_tables:
        op.execute('ALTER TABLE pdf_file_page_feedback RENAME TO document_page_feedback')
    if 'pdf_file_annotations' in existing_tables and 'annotations' not in existing_tables:
        op.execute('ALTER TABLE pdf_file_annotations RENAME TO annotations')
    
    # Audio tables
    if 'audio_files' in existing_tables and 'audios' not in existing_tables:
        op.execute('ALTER TABLE audio_files RENAME TO audios')
    if 'audio_file_extraction_jobs' in existing_tables and 'audio_extraction_jobs' not in existing_tables:
        op.execute('ALTER TABLE audio_file_extraction_jobs RENAME TO audio_extraction_jobs')
    if 'audio_file_content' in existing_tables and 'audio_segment_content' not in existing_tables:
        op.execute('ALTER TABLE audio_file_content RENAME TO audio_segment_content')
    if 'audio_file_feedback' in existing_tables and 'audio_segment_feedback' not in existing_tables:
        op.execute('ALTER TABLE audio_file_feedback RENAME TO audio_segment_feedback')
    if 'audio_file_annotations' in existing_tables and 'audio_annotations' not in existing_tables:
        op.execute('ALTER TABLE audio_file_annotations RENAME TO audio_annotations')
    
    # Image tables
    if 'image_files' in existing_tables and 'images' not in existing_tables:
        op.execute('ALTER TABLE image_files RENAME TO images')
    if 'image_file_extraction_jobs' in existing_tables and 'image_extraction_jobs' not in existing_tables:
        op.execute('ALTER TABLE image_file_extraction_jobs RENAME TO image_extraction_jobs')

