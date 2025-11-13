"""
PDF routes for the PDF Extraction Tool API
"""
import uuid
import aioboto3
import json
import PyPDF2
import math
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import Depends, File, UploadFile, HTTPException, Form, APIRouter, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, func
from sqlalchemy.orm import joinedload
from loguru import logger

from src.db import get_db
from src.models import (
    PDFFile,
    PDFExtractorType,
    PDFFileExtractionJob,
    PDFFilePageContent,
    PDFFilePageFeedback,
    DocumentResponse,
    DocumentExtractionJobResponse,
    DocumentPageContentResponse,
    DocumentPageFeedbackRequest,
    DocumentPageFeedbackResponse,
    PDFProject,
    ProjectCreateRequest,
    ExtractorCategory,
    ExtractorInfo,
    ExtractorsResponse,
    ExtractionStatus,
    ProjectResponse,
    User,
    MultipleUploadResponse,
    PaginationMeta,
    PaginatedDocumentsResponse,
    PDFFileAnnotation,
    AnnotationCreateRequest,
    AnnotationResponse,
    UserRatingBreakdown,
    AnnotationListItem,
    ImageExtractorType,
)
from src.file_coordinator import register_extraction_tasks
from src.tasks import process_document_with_extractor
from src.factory.pdf import get_reader, READER_MAP
from src.factory.image import get_image_reader
from src.auth.security import get_current_user
from src.cost_calculator import cost_calculator
from src.constants import (
    AWS_BUCKET_NAME,
    AWS_REGION,
    UPLOADS_DIR,
    FILE_CLEANUP_TTL_SECONDS,
    is_s3_available,
)
from src.routes.utils import (
    to_utc_isoformat,
    get_extractor_display_name,
    safe_content_disposition,
)

router = APIRouter()


async def start_background_tasks_for_documents(
    db: AsyncSession, document_data: List[Dict[str, str]], selected_extractor_list: List[str]
):
    """Create extraction jobs for all documents and register them for background processing"""
    for doc_info in document_data:
        document_uuid = doc_info["uuid"]
        
        # Create extraction jobs for each selected extractor
        job_uuids = []
        for extractor_name in selected_extractor_list:
            job_uuid = str(uuid.uuid4())
            extraction_job = PDFFileExtractionJob(
                uuid=job_uuid,
                pdf_file_uuid=document_uuid,
                extractor=extractor_name,
                status=ExtractionStatus.NOT_STARTED,
            )
            db.add(extraction_job)
            job_uuids.append(job_uuid)
        
        # Register extraction tasks for this document
        register_extraction_tasks(document_uuid, job_uuids, FILE_CLEANUP_TTL_SECONDS)
    
    # Commit all extraction jobs
    await db.commit()
    
    # Start background processing for each document and extractor
    for doc_info in document_data:
        document_uuid = doc_info["uuid"]
        file_path = doc_info["file_path"]
        
        # Fetch the document's extraction jobs
        result = await db.execute(
            select(PDFFileExtractionJob).where(
                PDFFileExtractionJob.pdf_file_uuid == document_uuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
        )
        jobs = result.scalars().all()
        
        # Queue each job
        for job in jobs:
            process_document_with_extractor.delay(
                job.uuid, document_uuid, file_path, job.extractor
            )


@router.get("/extractors", response_model=ExtractorsResponse)
async def get_extractors():
    """
    Get list of available PDF and image extractors with their metadata and cost information.
    
    Returns:
        ExtractorsResponse: Dictionary containing PDF and image extractors grouped by category
                           (OCR, Layout, Vision, Table, Other for PDFs; OCR, Vision for images),
                           with each extractor's ID, name, description, cost per page/image,
                           and supported tags.
    """
    try:
        logger.info("Fetching available PDF and image extractors")
        
        def pdf_reader_info(extractor_type: str) -> ExtractorInfo:
            try:
                reader_inst = get_reader(extractor_type)
                reader_meta = reader_inst.get_information()
                display_name = reader_meta.get("name", extractor_type)
                
                # Calculate cost per page using CostCalculator
                # Map display names to cost calculator keys for PDF extractors
                usage_data = {"page_count": 1}
                
                # Special handling for extractors with display name mismatches
                cost_name = display_name
                if extractor_type == "AzureDI" or display_name == "Azure Document Intelligence":
                    # For PDFs, cost calculator uses "Azure Document Intelligence PDF" or "AzureDI"
                    # Try "Azure Document Intelligence PDF" first, then "AzureDI"
                    cost_name = "Azure Document Intelligence PDF"
                elif display_name.startswith("OpenAI "):
                    # For vision models, use the extractor_type (gpt-4o-mini, gpt-4o, gpt-5, gpt-5-mini)
                    # which the cost calculator has entries for
                    cost_name = extractor_type
                
                cost_metrics = cost_calculator.calculate_cost(cost_name, usage_data)
                # If still default cost (0.001 is the default for unknown extractors), try extractor_type as fallback
                if abs(cost_metrics.calculated_cost - 0.001) < 0.0001:
                    # For AzureDI, also try the extractor_type directly
                    if extractor_type == "AzureDI":
                        cost_metrics = cost_calculator.calculate_cost("AzureDI", usage_data)
                    else:
                        cost_metrics = cost_calculator.calculate_cost(extractor_type, usage_data)
                cost_per_page = cost_metrics.calculated_cost
                
                return ExtractorInfo(
                    id=extractor_type,
                    name=display_name,
                    description=reader_meta.get("description", f"PDF extractor {extractor_type}"),
                    cost_per_page=cost_per_page,
                    support_tags=reader_meta.get("supports", ["Text", "Images"]),
                )
            except Exception:
                # Fallback: calculate cost even if get_information fails
                usage_data = {"page_count": 1}
                cost_metrics = cost_calculator.calculate_cost(extractor_type, usage_data)
                cost_per_page = cost_metrics.calculated_cost
                
                return ExtractorInfo(
                    id=extractor_type,
                    name=extractor_type,
                    description=f"PDF extractor {extractor_type}",
                    cost_per_page=cost_per_page,
                    support_tags=["Text", "Images"],
                )

        def image_reader_info(extractor_type: str) -> ExtractorInfo:
            try:
                reader_inst = get_image_reader(extractor_type)
                reader_meta = reader_inst.get_information()
                display_name = reader_meta.get("name", extractor_type)
                
                # Calculate cost per image using CostCalculator
                # Try display name first, then fallback to extractor_type
                usage_data = {"image_count": 1}
                cost_metrics = cost_calculator.calculate_cost(display_name, usage_data)
                if math.isclose(cost_metrics.calculated_cost, 0.001, rel_tol=1e-09, abs_tol=1e-09):  # Default cost, try extractor_type
                    cost_metrics = cost_calculator.calculate_cost(extractor_type, usage_data)
                cost_per_image = cost_metrics.calculated_cost
                
                return ExtractorInfo(
                    id=extractor_type,
                    name=display_name,
                    description=reader_meta.get("description", f"Image extractor {extractor_type}"),
                    cost_per_page=cost_per_image,  # Stored as cost per image for display
                    support_tags=reader_meta.get("supports", ["Text"]),
                )
            except Exception:
                # Fallback: calculate cost even if get_information fails
                usage_data = {"image_count": 1}
                cost_metrics = cost_calculator.calculate_cost(extractor_type, usage_data)
                cost_per_image = cost_metrics.calculated_cost
                
                return ExtractorInfo(
                    id=extractor_type,
                    name=extractor_type,
                    description=f"Image extractor {extractor_type}",
                    cost_per_page=cost_per_image,
                    support_tags=["Text"],
                )

        # Get PDF extractors
        # Exclude Camelot, Tabula, and Unstructured as they are causing failures
        excluded_extractors = {"Camelot", "Tabula", "Unstructured"}
        available_pdf_extractors = []
        for extractor_type in PDFExtractorType:
            if extractor_type.value not in excluded_extractors:
                available_pdf_extractors.append(pdf_reader_info(extractor_type.value))
        
        # Categorize PDF extractors
        ocr_ids = {"Tesseract", "Textract", "Mathpix", "AzureDI"}
        layout_ids = {"PDFPlumber", "PyPDF2", "PyMuPDF"}
        vision_ids = {"gpt-4o-mini", "gpt-4o", "gpt-5", "gpt-5-mini"}

        table_ids = set()  # No table extractors available (Camelot, Tabula disabled)
        
        ocr_extractors = [ext for ext in available_pdf_extractors if ext.id in ocr_ids]
        layout_extractors = [ext for ext in available_pdf_extractors if ext.id in layout_ids]
        vision_extractors = [ext for ext in available_pdf_extractors if ext.id in vision_ids]
        table_extractors = [ext for ext in available_pdf_extractors if ext.id in table_ids]
        other_extractors = [
            ext for ext in available_pdf_extractors 
            if ext.id not in (ocr_ids | layout_ids | vision_ids | table_ids)
        ]
        
        pdf_extractors_list = []
        if ocr_extractors:
            pdf_extractors_list.append({"category": "OCR", "extractors": ocr_extractors})
        if layout_extractors:
            pdf_extractors_list.append({"category": "Layout", "extractors": layout_extractors})
        if vision_extractors:
            pdf_extractors_list.append({"category": "Vision", "extractors": vision_extractors})
        if table_extractors:
            pdf_extractors_list.append({"category": "Table", "extractors": table_extractors})
        if other_extractors:
            pdf_extractors_list.append({"category": "Other", "extractors": other_extractors})
        
        # Get image extractors
        available_image_extractors = []
        for extractor_type in ImageExtractorType:
            available_image_extractors.append(image_reader_info(extractor_type.value))
        
        # Categorize image extractors
        image_ocr_extractors = [ext for ext in available_image_extractors if ext.id in ocr_ids]
        image_vision_extractors = [ext for ext in available_image_extractors if ext.id in vision_ids]
        
        image_extractors_list = []
        if image_ocr_extractors:
            image_extractors_list.append({"category": "OCR", "extractors": image_ocr_extractors})
        if image_vision_extractors:
            image_extractors_list.append({"category": "Vision", "extractors": image_vision_extractors})
        
        logger.info(f"Found {len(available_pdf_extractors)} PDF extractors and {len(available_image_extractors)} image extractors")
        return {
            "pdf_extractors": pdf_extractors_list,
            "image_extractors": image_extractors_list
        }
    except Exception as e:
        logger.error(f"Error fetching extractors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch extractors")


@router.post(
    "/projects/{project_uuid}/upload-multiple", response_model=MultipleUploadResponse
)
async def upload_multiple_documents(
    project_uuid: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db, use_cache=True),
    user: User = Depends(get_current_user, use_cache=True),
    selected_extractors: str = Form(""),
):
    """
    Upload multiple PDF files and create documents with extraction jobs for all extractors.
    Note: Image files should be uploaded via /image/projects/{project_uuid}/upload-multiple
    
    Args:
        project_uuid: UUID of the project to upload files to.
        files: List of PDF files to upload.
        db: Database session.
        user: Current authenticated user.
        selected_extractors: JSON string of extractor names to use (defaults to all PDF extractors).
    
    Returns:
        MultipleUploadResponse: Success message, list of uploaded document UUIDs, and list of failed uploads with errors.
    
    Raises:
        HTTPException: 400 if no files provided or invalid extractor format.
        HTTPException: 404 if project not found.
    """
    logger.info(f"Uploading {len(files)} PDF files to project: project_uuid={project_uuid}, user_id={user.id}")
    if not files:
        logger.warning(f"No files provided for upload: project_uuid={project_uuid}, user_id={user.id}")
        raise HTTPException(status_code=400, detail="At least one file is required")
    document_uuids = []
    failed_uploads = []
    document_data = []  # Store document info for background task creation
    # Parse selected extractors once
    try:
        if selected_extractors:
            selected_extractor_list = json.loads(selected_extractors)
        else:
            # Default to all PDF extractors (will be adjusted per file)
            selected_extractor_list = [
                extractor.value for extractor in PDFExtractorType
            ]
    except json.JSONDecodeError as e:
        logger.error(f"Invalid selected_extractors format: {selected_extractors}, error={str(e)}")
        raise HTTPException(
            status_code=400, detail="Invalid selected_extractors format"
        )
    # Phase 1: Upload all files and create document records
    logger.info(f"Starting PDF upload for project {project_uuid}: {len(files)} file(s) from user {user.id}")
    for file in files:
        try:
            if file.filename is None:
                error_msg = "File name is required"
                logger.error(f"PDF upload failed: {error_msg} for file with no filename in project {project_uuid}")
                failed_uploads.append(
                    {"filename": "unknown", "error": error_msg}
                )
                continue
            # Validate file type - only PDFs allowed
            filename_lower = file.filename.lower()
            if not filename_lower.endswith(".pdf"):
                error_msg = "Only PDF files are allowed. Use /image/projects/{project_uuid}/upload-multiple for image files."
                logger.error(f"PDF upload failed: {error_msg} for file '{file.filename}' in project {project_uuid}")
                failed_uploads.append(
                    {
                        "filename": file.filename,
                        "error": error_msg,
                    }
                )
                continue
            
            file_type = "pdf"
            # Generate unique document UUID
            document_uuid = str(uuid.uuid4())
            # Read once for validation
            content = await file.read()
            file_size_mb = len(content) / (1024 * 1024)
            MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
            if len(content) > MAX_UPLOAD_BYTES:
                error_msg = "File too large (max 20MB)"
                logger.error(f"PDF upload failed: {error_msg} for file '{file.filename}' (size: {file_size_mb:.2f} MB) in project {project_uuid}")
                failed_uploads.append(
                    {"filename": file.filename, "error": error_msg}
                )
                continue
            if file_type == "pdf" and not content.startswith(b"%PDF"):
                error_msg = "Invalid PDF file"
                logger.error(f"PDF upload failed: {error_msg} for file '{file.filename}' in project {project_uuid} - file does not start with PDF header")
                failed_uploads.append(
                    {"filename": file.filename, "error": error_msg}
                )
                continue
            # Conditional storage based on S3 availability
            if is_s3_available():
                # S3 available - store only in S3
                s3_key = f"projects/{project_uuid}/documents/{document_uuid}/v1/{file.filename}"
                # Upload to S3
                session = aioboto3.Session()
                async with session.client("s3", region_name=AWS_REGION) as s3:
                    await s3.put_object(
                        Bucket=AWS_BUCKET_NAME,
                        Key=s3_key,
                        Body=content,
                    )

                # Store S3 key in database instead of local path
                filepath = s3_key
                file_path = None  # No local file path
                logger.info(f"File stored in S3: {s3_key}")

            else:
                # No S3 - store locally
                file_path = UPLOADS_DIR / f"{document_uuid}_{file.filename}"
                filename_on_disk = file_path.name

                # Save locally
                with open(file_path, "wb") as buffer:
                    buffer.write(content)

                # Store local path in database
                filepath = str(Path("uploads") / filename_on_disk)
                logger.info(f"File stored locally: {file_path}")

            # Count pages for PDF
            page_count = None
            try:
                # Use content directly for page counting (works for both S3 and local)
                pdf_reader = PyPDF2.PdfReader(BytesIO(content))
                page_count = len(pdf_reader.pages)
            except Exception as e:
                logger.warning(
                    f"Could not count pages for {file.filename}: {str(e)}"
                )

            # Create document record
            document = PDFFile(
                uuid=document_uuid,
                filename=file.filename,
                filepath=filepath,
                page_count=page_count,
                project_uuid=project_uuid,
                user_id=user.id,
            )
            db.add(document)

            # Store document info for background task creation
            document_data.append(
                {
                    "uuid": document_uuid,
                    "file_path": filepath,  # Use the stored path (S3 key or local path)
                }
            )

            document_uuids.append(document_uuid)
            logger.info(f"Successfully processed PDF file '{file.filename}' (UUID: {document_uuid}) in project {project_uuid}")

        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            logger.error(f"PDF upload failed: Exception while processing file '{file.filename}' in project {project_uuid}: {str(e)}", exc_info=True)
            failed_uploads.append(
                {"filename": file.filename or "unknown", "error": error_msg}
            )
            # Clean up local file if it was created (only for local storage)
            if "file_path" in locals() and file_path and file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"Cleaned up failed upload file: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up file {file_path}: {str(cleanup_error)}")

    # Phase 2: Commit all successful uploads to database
    await db.commit()
    logger.info(f"Committed {len(document_uuids)} successful PDF uploads to database for project {project_uuid}")

    # Phase 3: Start background tasks for all successfully uploaded documents
    if document_data:
        await start_background_tasks_for_documents(
            db, document_data, selected_extractor_list
        )
        await db.commit()  # Commit the extraction jobs
        logger.info(f"Created extraction jobs for {len(document_data)} documents in project {project_uuid}")

    # Log final summary
    if failed_uploads:
        logger.warning(f"PDF upload completed for project {project_uuid}: {len(document_uuids)} succeeded, {len(failed_uploads)} failed. Failed files: {[f.get('filename', 'unknown') for f in failed_uploads]}")
    else:
        logger.info(f"PDF upload completed successfully for project {project_uuid}: {len(document_uuids)} file(s) uploaded")

    return MultipleUploadResponse(
        message=f"Successfully uploaded {len(document_uuids)} files. {len(failed_uploads)} files failed.",
        document_uuids=document_uuids,
        failed_uploads=failed_uploads,
    )


@router.post("/create-project", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new PDF project.
    
    Args:
        project: Project creation request containing name and optional description.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ProjectResponse: Created project with UUID, name, description, creation timestamp,
                         owner name, and ownership flag.
    
    Raises:
        HTTPException: 500 if project creation fails.
    """
    try:
        logger.info(f"Creating PDF project: name={project.name}, user_id={user.id}")
        project_uuid = str(uuid.uuid4())
        new_project = PDFProject(
            uuid=project_uuid,
            name=project.name,
            description=project.description,
            user_id=user.id,
        )
        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)
        logger.info(f"Successfully created PDF project: uuid={project_uuid}, name={project.name}")
        return ProjectResponse(
            uuid=new_project.uuid,
            name=new_project.name,
            description=new_project.description,
            created_at=to_utc_isoformat(new_project.created_at),
            owner_name=user.name,
            is_owner=True,
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create PDF project: user_id={user.id}, name={project.name}, error={str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """
    List all non-deleted PDF projects, ordered by creation date (newest first).
    
    Args:
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[ProjectResponse]: List of PDF projects with ownership information.
    """
    try:
        logger.info(f"Listing PDF projects for user_id={user.id}")
        # Show all projects regardless of owner, excluding deleted projects
        result = await db.execute(
            select(PDFProject)
            .options(joinedload(PDFProject.owner))
            .where(PDFProject.deleted_at.is_(None))
            .order_by(PDFProject.created_at.desc())
        )
        projects = result.scalars().all()
        logger.info(f"Found {len(projects)} PDF projects")
        return [
            ProjectResponse(
                uuid=p.uuid,
                name=p.name,
                description=p.description,
                created_at=to_utc_isoformat(p.created_at),
                owner_name=p.owner_name,
                is_owner=(p.user_id == user.id),
            )
            for p in projects
        ]
    except Exception as e:
        logger.error(f"Error listing PDF projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list PDF projects")


@router.get("/projects/{project_uuid}", response_model=ProjectResponse)
async def get_project(
    project_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get a specific PDF project by UUID.
    
    Args:
        project_uuid: UUID of the project to retrieve.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ProjectResponse: Project details with ownership information.
    
    Raises:
        HTTPException: 404 if project not found or has been deleted.
    """
    try:
        logger.info(f"Getting PDF project: project_uuid={project_uuid}, user_id={user.id}")
        # Allow any user to view any project, excluding deleted projects
        result = await db.execute(
            select(PDFProject).options(joinedload(PDFProject.owner)).where(
                PDFProject.uuid == project_uuid, PDFProject.deleted_at.is_(None)
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            logger.warning(f"PDF project not found: project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectResponse(
            uuid=p.uuid,
            name=p.name,
            description=p.description,
            created_at=to_utc_isoformat(p.created_at),
            owner_name=p.owner_name,
            is_owner=(p.user_id == user.id),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get PDF project")


@router.delete("/delete-project/{project_uuid}")
async def delete_project(
    project_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Soft delete a PDF project. Only the project owner or admin can delete.
    
    Args:
        project_uuid: UUID of the project to delete.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Success message confirming deletion.
    
    Raises:
        HTTPException: 404 if project not found.
        HTTPException: 403 if user is not the project owner or admin.
        HTTPException: 500 if deletion fails.
    """
    logger.info(f"Deleting PDF project: project_uuid={project_uuid}, user_id={user.id}")
    # Soft delete: mark project as deleted instead of removing from database
    try:
        # Only the owner (creator) or admin can delete the project
        result = await db.execute(
            select(PDFProject).where(
                PDFProject.uuid == project_uuid, PDFProject.deleted_at.is_(None)
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            logger.warning(f"PDF project not found for deletion: project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Project not found")
        is_admin = getattr(user, "role", "user") == "admin"
        if p.user_id != user.id and not is_admin:
            logger.warning(f"Unauthorized project deletion attempt: project_uuid={project_uuid}, user_id={user.id}, owner_id={p.user_id}")
            raise HTTPException(
                status_code=403, detail="Only the project owner or admin can delete this project"
            )

        # Set deleted_at timestamp instead of hard delete
        p.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Successfully deleted PDF project: project_uuid={project_uuid}, name={p.name}")
        return {"message": "Project deleted"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get(
    "/projects/{project_uuid}/documents", response_model=PaginatedDocumentsResponse
)
async def list_project_documents(
    project_uuid: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "uploaded_at",
    sort_direction: str = "desc",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List documents in a project with pagination and sorting.

    Args:
        project_uuid: Project identifier
        page: Page number (1-based, default: 1)
        page_size: Number of documents per page (default: 10)
        sort_by: Field to sort by. Valid options: uploaded_at, filename, file_type, page_count, owner_name, uuid (default: uploaded_at)
        sort_direction: Sort direction. Valid options: asc, desc (default: desc)

    Returns:
        PaginatedDocumentsResponse: Contains documents list and pagination metadata

    Raises:
        HTTPException: 404 if project not found
        HTTPException: 400 if invalid pagination or sorting parameters
    """
    try:
        # Verify that the project exists (visible to all users), excluding deleted projects
        project_result = await db.execute(
            select(PDFProject).where(
                PDFProject.uuid == project_uuid, PDFProject.deleted_at.is_(None)
            )
        )
        if not project_result.scalar_one_or_none():
            logger.warning(f"Project not found: project_uuid={project_uuid}")
            raise HTTPException(status_code=404, detail="Project not found")

        logger.info(f"Listing project documents: project_uuid={project_uuid}, page={page}, page_size={page_size}, sort_by={sort_by}, sort_direction={sort_direction}")
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be greater than 0")

        # Validate sorting parameters
        valid_sort_fields = [
            "uploaded_at",
            "filename",
            "file_type",
            "page_count",
            "owner_name",
            "uuid",
        ]
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}",
            )

        if sort_direction not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="Sort direction must be 'asc' or 'desc'"
            )

        # Get total count efficiently
        count_result = await db.execute(
            select(func.count(PDFFile.uuid)).where(
                PDFFile.project_uuid == project_uuid, PDFFile.deleted_at.is_(None)
            )
        )
        total_count = count_result.scalar()
        logger.info(f"Found {total_count} documents in project, returning page {page} of {math.ceil(total_count / page_size) if total_count > 0 else 1}")

        # Calculate pagination metadata
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        offset = (page - 1) * page_size

        # Build dynamic sorting
        # SECURITY: Whitelist allowed columns to prevent SQL injection
        ALLOWED_SORT_COLUMNS = {'uploaded_at', 'filename', 'page_count'}
        if sort_by not in ALLOWED_SORT_COLUMNS:
            raise HTTPException(status_code=400, detail="Invalid sort column")
        sort_column = getattr(PDFFile, sort_by)
        if sort_direction == "desc":
            order_clause = sort_column.desc()
        else:
            order_clause = sort_column.asc()
    except Exception as e:
        logger.error(f"Error listing project documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list project documents")

    # Get paginated documents
    result = await db.execute(
        select(PDFFile)
        .where(PDFFile.project_uuid == project_uuid, PDFFile.deleted_at.is_(None))
        .order_by(order_clause)
        .offset(offset)
        .limit(page_size)
    )
    docs = result.scalars().all()

    # Build response
    documents = [
        DocumentResponse(
            uuid=str(doc.uuid),
            filename=str(doc.filename),
            filepath=str(doc.filepath),
            uploaded_at=to_utc_isoformat(doc.uploaded_at),
            page_count=int(doc.page_count) if doc.page_count else None,
            file_type=str(doc.file_type),
            owner_name=doc.owner_name,
        )
        for doc in docs
    ]
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    return PaginatedDocumentsResponse(documents=documents, pagination=pagination)


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}",
    response_model=DocumentResponse,
)
async def get_document(
    project_uuid: str,
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get a specific document by UUID within a project.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        DocumentResponse: Document details including UUID, filename, filepath, upload timestamp,
                         page count, file type, and owner name.
    
    Raises:
        HTTPException: 404 if document or project not found.
    """
    logger.info(f"Getting document: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
    try:
        result = await db.execute(
            select(PDFFile).options(joinedload(PDFFile.owner)).where(
                PDFFile.uuid == document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        document = result.scalar_one_or_none()
    
        if not document:
            logger.warning(f"Document not found: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentResponse(
            uuid=str(document.uuid),
            filename=str(document.filename),
            filepath=str(document.filepath),
            uploaded_at=to_utc_isoformat(document.uploaded_at),
            page_count=int(document.page_count),
            file_type=str(document.file_type),
            owner_name=document.owner_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.delete("/projects/{project_uuid}/documents/{document_uuid}")
async def delete_document(
    project_uuid: str,
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Soft delete a document and all related data. Only the project owner or admin can delete.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document to delete.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Success message confirming deletion.
    
    Raises:
        HTTPException: 404 if document or project not found.
        HTTPException: 403 if user is not the project owner or admin.
        HTTPException: 500 if deletion fails.
    """
    logger.info(f"Deleting document: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
    # Verify project exists and requester is owner or admin, excluding deleted projects
    project_result = await db.execute(
        select(PDFProject).where(
            PDFProject.uuid == project_uuid, PDFProject.deleted_at.is_(None)
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        logger.warning(f"Project not found for document deletion: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
        raise HTTPException(status_code=404, detail="Project not found")
    is_admin = getattr(user, "role", "user") == "admin"
    if project.user_id != user.id and not is_admin:
        logger.warning(f"Unauthorized document deletion attempt: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}, owner_id={project.user_id}")
        raise HTTPException(
            status_code=403, detail="Only the project owner or admin can delete files"
        )

    # Fetch document within project, excluding already deleted documents
    doc_result = await db.execute(
        select(PDFFile).where(
            PDFFile.uuid == document_uuid,
            PDFFile.project_uuid == project_uuid,
            PDFFile.deleted_at.is_(None),
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        logger.warning(f"Document not found for deletion: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
        raise HTTPException(status_code=404, detail="Document not found")

    # Collect job UUIDs for cascading soft deletions
    jobs_result = await db.execute(
        select(PDFFileExtractionJob.uuid).where(
            PDFFileExtractionJob.pdf_file_uuid == document_uuid,
            PDFFileExtractionJob.deleted_at.is_(None),
        )
    )
    job_uuid_rows = jobs_result.all()
    job_uuids = [row[0] for row in job_uuid_rows]
    logger.info(f"Deleting document with {len(job_uuids)} related jobs: document_uuid={document_uuid}, filename={document.filename}")

    try:
        # Soft delete related rows instead of hard delete
        current_time = datetime.now(timezone.utc)

        if job_uuids:
            await db.execute(
                update(PDFFilePageContent)
                .where(PDFFilePageContent.extraction_job_uuid.in_(job_uuids))
                .values(deleted_at=current_time)
            )

        await db.execute(
            update(PDFFilePageFeedback)
            .where(PDFFilePageFeedback.pdf_file_uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        await db.execute(
            update(PDFFileAnnotation)
            .where(PDFFileAnnotation.pdf_file_uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        await db.execute(
            update(PDFFileExtractionJob)
            .where(PDFFileExtractionJob.pdf_file_uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        # Soft delete the document itself
        await db.execute(
            update(PDFFile)
            .where(PDFFile.uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        # Note: We keep the files (S3 and local) for potential recovery
        # Files can be cleaned up later by a separate cleanup job if needed

        await db.commit()
        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error(f"Error deleting document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.delete("/delete-document/{document_uuid}")
async def delete_document_legacy(
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Legacy soft delete endpoint to support older clients. Only project owner can delete.
    
    Args:
        document_uuid: UUID of the document to delete.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Success message confirming deletion.
    
    Raises:
        HTTPException: 404 if document or project not found.
        HTTPException: 403 if user is not the project owner.
        HTTPException: 500 if deletion fails.
    """
    logger.info(f"Deleting document (legacy endpoint): document_uuid={document_uuid}, user_id={user.id}")
    # Fetch document to determine project, excluding already deleted documents
    doc_result = await db.execute(
        select(PDFFile).where(
            PDFFile.uuid == document_uuid, PDFFile.deleted_at.is_(None)
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        logger.warning(f"Document not found for deletion (legacy): document_uuid={document_uuid}, user_id={user.id}")
        raise HTTPException(status_code=404, detail="Document not found")

    project_uuid = document.project_uuid
    project_result = await db.execute(
        select(PDFProject).where(
            PDFProject.uuid == project_uuid, PDFProject.deleted_at.is_(None)
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        logger.warning(f"Project not found for document deletion (legacy): project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        logger.warning(f"Unauthorized document deletion attempt (legacy): project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}, owner_id={project.user_id}")
        raise HTTPException(
            status_code=403, detail="Only the project owner can delete files"
        )

    # Collect job UUIDs for cascading soft deletions
    jobs_result = await db.execute(
        select(PDFFileExtractionJob.uuid).where(
            PDFFileExtractionJob.pdf_file_uuid == document_uuid,
            PDFFileExtractionJob.deleted_at.is_(None),
        )
    )
    job_uuid_rows = jobs_result.all()
    job_uuids = [row[0] for row in job_uuid_rows]

    try:
        # Soft delete related rows instead of hard delete
        current_time = datetime.now(timezone.utc)

        if job_uuids:
            await db.execute(
                update(PDFFilePageContent)
                .where(PDFFilePageContent.extraction_job_uuid.in_(job_uuids))
                .values(deleted_at=current_time)
            )

        await db.execute(
            update(PDFFilePageFeedback)
            .where(PDFFilePageFeedback.pdf_file_uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        await db.execute(
            update(PDFFileAnnotation)
            .where(PDFFileAnnotation.pdf_file_uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        await db.execute(
            update(PDFFileExtractionJob)
            .where(PDFFileExtractionJob.pdf_file_uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        # Soft delete the document itself
        await db.execute(
            update(PDFFile)
            .where(PDFFile.uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        # Note: We keep the files (S3 and local) for potential recovery
        # Files can be cleaned up later by a separate cleanup job if needed

        await db.commit()
        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error(f"Error deleting document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs",
    response_model=List[DocumentExtractionJobResponse],
)
async def get_document_extraction_jobs(
    project_uuid: str,
    document_uuid: str,
    filter_by_user: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all extraction jobs for a document with feedback statistics.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        filter_by_user: If True, only show ratings from the current user (default: False).
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[DocumentExtractionJobResponse]: List of extraction jobs with status, timing, cost,
                                            and feedback statistics.
    
    Raises:
        HTTPException: 404 if document not found.
    """
    try:
        logger.info(f"Getting extraction jobs: project_uuid={project_uuid}, document_uuid={document_uuid}, filter_by_user={filter_by_user}, user_id={user.id}")
        # First verify that the document belongs to the project (visible to all users)
        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        if not doc_result.scalar_one_or_none():
            logger.warning(f"Document not found: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")

        result = await db.execute(
            select(PDFFileExtractionJob)
            .where(
                PDFFileExtractionJob.pdf_file_uuid == document_uuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
            .order_by(PDFFileExtractionJob.extractor)
        )
        jobs = result.scalars().all()
        logger.info(f"Found {len(jobs)} extraction jobs for document: document_uuid={document_uuid}")

        # Get feedback statistics for each job
        job_responses = []
        for job in jobs:
            # Get all feedback for this extraction job, optionally filtered by user
            try:
                feedback_query = select(PDFFilePageFeedback).where(
                    PDFFilePageFeedback.extraction_job_uuid == job.uuid,
                    PDFFilePageFeedback.deleted_at.is_(None),
                )

                # Apply user filter if requested
                if filter_by_user:
                    feedback_query = feedback_query.where(
                        PDFFilePageFeedback.user_id == user.id
                    )

                feedback_result = await db.execute(feedback_query)
                feedbacks = feedback_result.scalars().all()

                # Calculate statistics
                total_feedback_count = len(feedbacks)
                pages_annotated = len(
                    set(f.page_number for f in feedbacks if f.rating is not None)
                )

                # Calculate average rating (safely get rating if it exists)
                ratings = [f.rating for f in feedbacks if f.rating is not None]
                total_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
            except Exception as e:
                # If user_id column doesn't exist in database yet, use defaults
                logger.warning(f"Could not fetch feedback stats (schema may need migration): {e}")
                total_feedback_count = 0
                pages_annotated = 0
                total_rating = None

            # Safely convert status to enum
            try:
                job_status = ExtractionStatus(job.status)
            except (ValueError, KeyError):
                # Handle legacy status values or invalid status
                job_status = ExtractionStatus.NOT_STARTED
            
            extractor_display_name = get_extractor_display_name(str(job.extractor), "document")
            job_responses.append(
                DocumentExtractionJobResponse(
                    uuid=str(job.uuid),
                    document_uuid=str(job.pdf_file_uuid),
                    extractor=str(job.extractor),
                    extractor_display_name=extractor_display_name,
                    status=job_status,
                    start_time=to_utc_isoformat(job.start_time) if job.start_time else None,
                    end_time=to_utc_isoformat(job.end_time) if job.end_time else None,
                    latency_ms=int(job.latency_ms or 0),
                    cost=float(job.cost or 0.0),
                    pages_annotated=pages_annotated,
                    total_rating=total_rating,
                    total_feedback_count=total_feedback_count,
                )
            )
        logger.info(f"Returning {len(job_responses)} extraction job responses: document_uuid={document_uuid}")
        return job_responses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document extraction jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get document extraction jobs")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs/{job_uuid}/pages",
    response_model=List[DocumentPageContentResponse],
)
async def get_extraction_job_pages(
    project_uuid: str,
    document_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all pages for an extraction job.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[DocumentPageContentResponse]: List of pages with content, metadata, and feedback.
    
    Raises:
        HTTPException: 404 if extraction job or document not found.
    """
    try:
        logger.info(f"Getting extraction job pages: project_uuid={project_uuid}, document_uuid={document_uuid}, job_uuid={job_uuid}, user_id={user.id}")
        # First verify that the extraction job belongs to a document owned by the user and project
        job_result = await db.execute(
            select(PDFFileExtractionJob).where(
                PDFFileExtractionJob.uuid == job_uuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(f"Extraction job not found: job_uuid={job_uuid}, document_uuid={document_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Extraction job not found")

        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        if not doc_result.scalar_one_or_none():
            logger.warning(f"Document not found: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")
        result = await db.execute(
            select(PDFFilePageContent)
            .where(
                PDFFilePageContent.extraction_job_uuid == job_uuid,
                PDFFilePageContent.deleted_at.is_(None),
            )
            .order_by(PDFFilePageContent.page_number)
        )
        pages = result.scalars().all()
        logger.info(f"Found {len(pages)} pages for job: job_uuid={job_uuid}, extractor={job.extractor}")
        return [
            DocumentPageContentResponse(
                uuid=str(page.uuid),
                extraction_job_uuid=str(page.extraction_job_uuid),
                page_number=int(page.page_number),
                content=dict(page.content),
            )
            for page in pages
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extraction job pages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get extraction job pages")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/pages/{page_number}/extractions",
    response_model=List[DocumentPageContentResponse],
)
async def get_page_extractions(
    project_uuid: str,
    document_uuid: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all extraction results for a specific page across all extractors.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        page_number: Page number to get extractions for.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[DocumentPageContentResponse]: List of page extractions from all extractors with feedback if available.
    
    Raises:
        HTTPException: 404 if document not found.
    """
    try:
        logger.info(f"Getting page extractions: project_uuid={project_uuid}, document_uuid={document_uuid}, page_number={page_number}, user_id={user.id}")
        # First verify that the document belongs to the user and project
        doc_result = await db.execute(
            select(PDFFile).where(
            PDFFile.uuid == document_uuid,
            PDFFile.project_uuid == project_uuid,
            PDFFile.deleted_at.is_(None),
        )
    )
        if not doc_result.scalar_one_or_none():
            logger.warning(f"Document not found: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")
        # Get all extraction jobs for this document
        jobs_result = await db.execute(
            select(PDFFileExtractionJob).where(
                PDFFileExtractionJob.pdf_file_uuid == document_uuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
        )
        jobs = jobs_result.scalars().all()
        logger.info(f"Found {len(jobs)} extraction jobs for page extractions: document_uuid={document_uuid}, page_number={page_number}")
        # Get page content for this specific page from all extraction jobs
        page_contents = []
        for job in jobs:
            result = await db.execute(
                select(PDFFilePageContent).where(
                    PDFFilePageContent.extraction_job_uuid == job.uuid,
                    PDFFilePageContent.page_number == page_number,
                    PDFFilePageContent.deleted_at.is_(None),
                )
            )
            page_content = result.scalar_one_or_none()
            if page_content:
                page_contents.append(page_content)
        # Get feedback for this page
        feedback_result = await db.execute(
            select(PDFFilePageFeedback).where(
                PDFFilePageFeedback.pdf_file_uuid == document_uuid,
                PDFFilePageFeedback.page_number == page_number,
                PDFFilePageFeedback.deleted_at.is_(None),
            )
        )
        feedbacks = feedback_result.scalars().all()
        # Create a mapping of extraction_job_uuid to feedback
        feedback_map = {f.extraction_job_uuid: f for f in feedbacks}
        logger.info(f"Found {len(page_contents)} page contents and {len(feedbacks)} feedback entries for page: document_uuid={document_uuid}, page_number={page_number}")
        return [
            DocumentPageContentResponse(
                uuid=str(page.uuid),
                extraction_job_uuid=str(page.extraction_job_uuid),
                page_number=int(page.page_number),
                content=dict(page.content),
                feedback=DocumentPageFeedbackResponse(
                    uuid=str(feedback.uuid),
                    document_uuid=str(feedback.pdf_file_uuid),
                    page_number=int(feedback.page_number),
                    extraction_job_uuid=str(feedback.extraction_job_uuid),
                    feedback_type=str(feedback.feedback_type),
                    rating=feedback.rating,
                    comment=feedback.comment,
                    user_id=feedback.user_id,
                    user_name=feedback.user_name,
                    created_at=to_utc_isoformat(feedback.created_at),
                )
                if feedback
                else None,
            )
            for page in page_contents
            for feedback in [feedback_map.get(page.extraction_job_uuid)]
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page extractions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get page extractions")


@router.post(
    "/projects/{project_uuid}/documents/{document_uuid}/feedback",
    response_model=DocumentPageFeedbackResponse,
)
async def submit_feedback(
    project_uuid: str,
    document_uuid: str,
    feedback: DocumentPageFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submit or update feedback (rating and/or comment) for a specific page extraction.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        feedback: Feedback request containing page number, extraction job UUID, rating, and comment.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        DocumentPageFeedbackResponse: Created or updated feedback with user information and timestamp.
    
    Raises:
        HTTPException: 404 if document not found.
        HTTPException: 500 if feedback submission fails.
    """
    logger.info(f"Submitting feedback: project_uuid={project_uuid}, document_uuid={document_uuid}, page_number={feedback.page_number}, job_uuid={feedback.extraction_job_uuid}, user_id={user.id}, rating={feedback.rating}")
    try:
        # First verify that the document exists in the given project (accessible to any user)
        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == feedback.document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        if not doc_result.scalar_one_or_none():
            logger.warning(f"Document not found for feedback: document_uuid={feedback.document_uuid}, project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")
        # Check if feedback already exists for this page, extractor, and user
        existing_feedback = await db.execute(
            select(PDFFilePageFeedback).where(
                PDFFilePageFeedback.pdf_file_uuid == feedback.document_uuid,
                PDFFilePageFeedback.page_number == feedback.page_number,
                PDFFilePageFeedback.extraction_job_uuid
                == feedback.extraction_job_uuid,
                PDFFilePageFeedback.user_id == user.id,
                PDFFilePageFeedback.deleted_at.is_(None),
            )
        )
        existing = existing_feedback.scalar_one_or_none()
        if existing:
            # Update existing feedback
            if feedback.rating is not None:
                existing.rating = feedback.rating
            if feedback.comment is not None:
                existing.comment = feedback.comment
            # Update user info (do not set user_name; column not stored)
            existing.user_id = user.id
            await db.commit()
            logger.info(f"Updated existing feedback: feedback_uuid={existing.uuid}, page_number={feedback.page_number}, rating={feedback.rating}")
        else:
            # Create new feedback
            feedback_uuid = str(uuid.uuid4())
            new_feedback = PDFFilePageFeedback(
                uuid=feedback_uuid,
                pdf_file_uuid=feedback.document_uuid,
                page_number=feedback.page_number,
                extraction_job_uuid=feedback.extraction_job_uuid,
                feedback_type="single",
                rating=feedback.rating,
                comment=feedback.comment,
                user_id=user.id,
            )
            db.add(new_feedback)
            await db.commit()
            await db.refresh(new_feedback)
            logger.info(f"Created new feedback: feedback_uuid={feedback_uuid}, page_number={feedback.page_number}, rating={feedback.rating}")
        # Return the updated/created feedback
        if existing:
            return DocumentPageFeedbackResponse(
                uuid=str(existing.uuid),
                document_uuid=str(existing.pdf_file_uuid),
                page_number=int(existing.page_number),
                extraction_job_uuid=str(existing.extraction_job_uuid),
                feedback_type=str(existing.feedback_type),
                rating=existing.rating,
                comment=existing.comment,
                user_id=existing.user_id,
                user_name=user.name,
                created_at=to_utc_isoformat(existing.created_at),
            )
        else:
            # Refresh to get the created object
            await db.refresh(new_feedback)
            return DocumentPageFeedbackResponse(
                uuid=str(new_feedback.uuid),
                document_uuid=str(new_feedback.pdf_file_uuid),
                page_number=int(new_feedback.page_number),
                extraction_job_uuid=str(new_feedback.extraction_job_uuid),
                feedback_type=str(new_feedback.feedback_type),
                rating=new_feedback.rating,
                comment=new_feedback.comment,
                user_id=new_feedback.user_id,
                user_name=user.name,
                created_at=to_utc_isoformat(new_feedback.created_at),
            )

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/pages/{page_number}/feedback",
    response_model=List[DocumentPageFeedbackResponse],
)
async def get_page_feedback(
    project_uuid: str,
    document_uuid: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all feedback entries for a specific page, ordered by creation date (newest first).
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        page_number: Page number to get feedback for.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[DocumentPageFeedbackResponse]: List of feedback entries with ratings, comments, and user information.
    
    Raises:
        HTTPException: 404 if document not found.
        HTTPException: 500 if error occurs.
    """
    try:
        logger.info(f"Getting page feedback: project_uuid={project_uuid}, document_uuid={document_uuid}, page_number={page_number}, user_id={user.id}")
        try:
            # Verify that the document belongs to the project (visible to all users)
            doc_result = await db.execute(
                select(PDFFile).where(
                    PDFFile.uuid == document_uuid,
                    PDFFile.project_uuid == project_uuid,
                    PDFFile.deleted_at.is_(None),
                )
            )
            if not doc_result.scalar_one_or_none():
                logger.warning(f"Document not found for feedback retrieval: document_uuid={document_uuid}, project_uuid={project_uuid}, user_id={user.id}")
                raise HTTPException(status_code=404, detail="Document not found")
            result = await db.execute(
                select(PDFFilePageFeedback).where(
                    PDFFilePageFeedback.pdf_file_uuid == document_uuid,
                    PDFFilePageFeedback.page_number == page_number,
                    PDFFilePageFeedback.deleted_at.is_(None),
                )
            )
            feedbacks = result.scalars().all()
            logger.info(f"Found {len(feedbacks)} feedback entries for page: document_uuid={document_uuid}, page_number={page_number}")
            return [
                DocumentPageFeedbackResponse(
                    uuid=str(feedback.uuid),
                    document_uuid=str(feedback.pdf_file_uuid),
                    page_number=int(feedback.page_number),
                    extraction_job_uuid=str(feedback.extraction_job_uuid),
                    feedback_type=str(feedback.feedback_type),
                    rating=feedback.rating,
                    comment=feedback.comment,
                    user_id=feedback.user_id,
                    # DocumentPageFeedback does not persist user_name; return None to avoid attribute errors
                    user_name=None,
                    created_at=to_utc_isoformat(feedback.created_at),
                )
                for feedback in feedbacks
            ]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting page feedback: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get page feedback")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get page feedback")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs/{job_uuid}/rating-breakdown",
    response_model=List[UserRatingBreakdown],
)
async def get_rating_breakdown(
    project_uuid: str,
    document_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get user-wise rating breakdown for an extraction job.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[UserRatingBreakdown]: List of user rating breakdowns with average ratings, pages rated,
                                   total ratings, and latest comments.
    
    Raises:
        HTTPException: 404 if document or extraction job not found.
        HTTPException: 500 if error occurs.
    """
    logger.info(f"Getting rating breakdown: project_uuid={project_uuid}, document_uuid={document_uuid}, job_uuid={job_uuid}, user_id={user.id}")
    try:
        # Verify document exists in project
        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        if not doc_result.scalar_one_or_none():
            logger.warning(f"Document not found for rating breakdown: document_uuid={document_uuid}, project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")

        # Verify extraction job exists
        job_result = await db.execute(
            select(PDFFileExtractionJob).where(
                PDFFileExtractionJob.uuid == job_uuid,
                PDFFileExtractionJob.pdf_file_uuid == document_uuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
        )
        if not job_result.scalar_one_or_none():
            logger.warning(f"Extraction job not found for rating breakdown: job_uuid={job_uuid}, document_uuid={document_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Get all feedback for this extraction job, grouped by user
        feedback_result = await db.execute(
            select(PDFFilePageFeedback)
            .where(
                PDFFilePageFeedback.extraction_job_uuid == job_uuid,
                PDFFilePageFeedback.deleted_at.is_(None),
            )
            .order_by(PDFFilePageFeedback.created_at.desc())
        )
        feedbacks = feedback_result.scalars().all()

        # Group by user
        user_feedback_map: Dict[Optional[int], List] = {}
        for feedback in feedbacks:
            user_id = feedback.user_id
            if user_id not in user_feedback_map:
                user_feedback_map[user_id] = []
            user_feedback_map[user_id].append(feedback)

        # Fetch user names in batch
        user_ids = [uid for uid in user_feedback_map.keys() if uid is not None]
        user_id_to_name: Dict[int, str] = {}
        if user_ids:
            users_result = await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
            for uid, name in users_result.all():
                user_id_to_name[int(uid)] = name

        # Build breakdown
        breakdown = []
        for user_id, user_feedbacks in user_feedback_map.items():
            ratings = [f.rating for f in user_feedbacks if f.rating is not None]
            if not ratings:
                continue

            avg_rating = sum(ratings) / len(ratings)
            pages_rated = len(set(f.page_number for f in user_feedbacks))
            latest = user_feedbacks[0]  # Already sorted by created_at desc

            breakdown.append(
                UserRatingBreakdown(
                    user_id=user_id,
                    user_name=user_id_to_name.get(int(user_id)) if user_id is not None else "Unknown User",
                    average_rating=round(avg_rating, 2),
                    pages_rated=pages_rated,
                    total_ratings=len(ratings),
                    latest_comment=latest.comment,
                    latest_rated_at=to_utc_isoformat(latest.created_at),
                )
            )

        logger.info(f"Returning rating breakdown: job_uuid={job_uuid}, users={len(breakdown)}, total_feedbacks={len(feedbacks)}")
        return breakdown

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rating breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get rating breakdown")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/pages/{page_number}/average-rating",
)
async def get_page_average_rating(
    project_uuid: str,
    document_uuid: str,
    page_number: int,
    extraction_job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get average rating for a specific page and extraction job, including the current user's rating.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        page_number: Page number to get average rating for.
        extraction_job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Dictionary containing average_rating (rounded to 2 decimals), total_ratings count,
              and user_rating (current user's rating if available, None otherwise).
              Returns None for average_rating if no ratings exist.
    
    Raises:
        HTTPException: 404 if document not found.
        HTTPException: 500 if error occurs.
    """
    try:
        logger.info(f"Getting page average rating: project_uuid={project_uuid}, document_uuid={document_uuid}, page_number={page_number}, job_uuid={extraction_job_uuid}, user_id={user.id}")
        try:
            # Verify document exists in project
            doc_result = await db.execute(
                select(PDFFile).where(
                    PDFFile.uuid == document_uuid,
                    PDFFile.project_uuid == project_uuid,
                    PDFFile.deleted_at.is_(None),
                )
            )
            if not doc_result.scalar_one_or_none():
                logger.warning(f"Document not found for average rating: document_uuid={document_uuid}, project_uuid={project_uuid}, user_id={user.id}")
                raise HTTPException(status_code=404, detail="Document not found")

            # Get all ratings for this page and specific extractor
            feedback_result = await db.execute(
                select(PDFFilePageFeedback).where(
                    PDFFilePageFeedback.pdf_file_uuid == document_uuid,
                    PDFFilePageFeedback.page_number == page_number,
                    PDFFilePageFeedback.extraction_job_uuid == extraction_job_uuid,
                    PDFFilePageFeedback.rating.isnot(None),
                    PDFFilePageFeedback.deleted_at.is_(None),
                )
            )
            feedbacks = feedback_result.scalars().all()

            if not feedbacks:
                logger.info(f"No ratings found for page: document_uuid={document_uuid}, page_number={page_number}, job_uuid={extraction_job_uuid}")
                return {"average_rating": None, "total_ratings": 0, "user_rating": None}

            ratings = [f.rating for f in feedbacks]
            average_rating = round(sum(ratings) / len(ratings), 2)

            # Get current user's rating for this page and extractor
            user_rating = None
            for feedback in feedbacks:
                if feedback.user_id == user.id:
                    user_rating = feedback.rating
                    break

            return {
                "average_rating": average_rating,
                "total_ratings": len(ratings),
                "user_rating": user_rating,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting page average rating: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get page average rating")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page average rating: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get page average rating")


@router.get(
    "/projects/{project_uuid}/documents/{document_uuid}/annotations-list",
    response_model=List[AnnotationListItem],
)
async def get_annotations_list(
    project_uuid: str,
    document_uuid: str,
    extractor_uuid: Optional[str] = None,
    user_id: Optional[int] = None,
    page_number: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List annotations for a document with optional filters.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        extractor_uuid: Optional UUID of extraction job to filter by.
        user_id: Optional user ID to filter by.
        page_number: Optional page number to filter by.
        search: Optional search string to filter by text or comment.
        db: Database session.
        current_user: Current authenticated user.
    
    Returns:
        List[AnnotationListItem]: List of annotations ordered by page number and creation date.
    
    Raises:
        HTTPException: 404 if document not found.
        HTTPException: 500 if error occurs.
    """
    try:
        logger.info(f"Getting annotations list: project_uuid={project_uuid}, document_uuid={document_uuid}, extractor_uuid={extractor_uuid}, user_id={user_id}, page_number={page_number}, search={search}, user_id={current_user.id}")
        try:
            # Verify document exists in project
            doc_result = await db.execute(
                select(PDFFile).where(
                    PDFFile.uuid == document_uuid,
                    PDFFile.project_uuid == project_uuid,
                    PDFFile.deleted_at.is_(None),
                )
            )
            if not doc_result.scalar_one_or_none():
                logger.warning(f"Document not found for annotations list: document_uuid={document_uuid}, project_uuid={project_uuid}, user_id={current_user.id}")
                raise HTTPException(status_code=404, detail="Document not found")

            # Build query with filters
            query = (
                select(PDFFileAnnotation, PDFFileExtractionJob)
                .join(
                    PDFFileExtractionJob,
                    PDFFileAnnotation.extraction_job_uuid == PDFFileExtractionJob.uuid,
                )
                .where(
                    PDFFileAnnotation.pdf_file_uuid == document_uuid,
                    PDFFileAnnotation.deleted_at.is_(None),
                    PDFFileExtractionJob.deleted_at.is_(None),
                )
            )

            if extractor_uuid:
                query = query.where(PDFFileAnnotation.extraction_job_uuid == extractor_uuid)
            if user_id is not None:
                query = query.where(PDFFileAnnotation.user_id == user_id)
            if page_number is not None:
                query = query.where(PDFFileAnnotation.page_number == page_number)
            if search:
                search_pattern = f"%{search}%"
                query = query.where(
                    or_(
                        PDFFileAnnotation.text.ilike(search_pattern),
                        PDFFileAnnotation.comment.ilike(search_pattern),
                    )
                )

            query = query.order_by(
                PDFFileAnnotation.page_number.asc(), PDFFileAnnotation.created_at.desc()
            )

            result = await db.execute(query)
            rows = result.all()
            logger.info(f"Found {len(rows)} annotations: document_uuid={document_uuid}, filters=extractor_uuid={extractor_uuid}, user_id={user_id}, page_number={page_number}, search={search}")

            return [
                AnnotationListItem(
                    uuid=str(annotation.uuid),
                    page_number=int(annotation.page_number),
                    extractor=job.extractor,
                    extraction_job_uuid=str(annotation.extraction_job_uuid),
                    user_id=annotation.user_id,
                    user_name=annotation.user_name or "Unknown User",
                    text=str(annotation.text or ""),
                    comment=annotation.comment or "",
                    selection_start=int(annotation.selection_start),
                    selection_end=int(annotation.selection_end),
                    created_at=to_utc_isoformat(annotation.created_at),
                )
                for annotation, job in rows
            ]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting annotations list: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get annotations list")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting annotations list: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get annotations list")


# Robust, auth-protected download endpoint that serves files from S3
@router.get("/projects/{project_uuid}/documents/{document_uuid}/pdf-load")
## TODO: What is the best approach for sharing images and pdf?
async def download_document_file(
    project_uuid: str,
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Download a PDF document file from S3 or local storage.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document to download.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        Response: PDF file content with appropriate Content-Type and Content-Disposition headers.
    
    Raises:
        HTTPException: 404 if document not found or file does not exist on server.
    """
    try:
        logger.info(f"Downloading document file: project_uuid={project_uuid}, document_uuid={document_uuid}, user_id={user.id}")
        # Allow any authenticated user to download within the same project context
        result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            logger.warning(f"Document not found for download: document_uuid={document_uuid}, project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")
        logger.info(f"Loading file for document {document_uuid}: filepath={document.filepath}, filename={document.filename}")
        # Documents are PDF-only
        media_type = "application/pdf"
        # Conditional file serving based on storage type
        if document.filepath.startswith("projects/"):
            # File is stored in S3
            try:
                logger.info(f"Attempting to load from S3: {document.filepath}")
                # Download file from S3
                session = aioboto3.Session()
                async with session.client("s3", region_name=AWS_REGION) as s3:
                    response = await s3.get_object(
                        Bucket=AWS_BUCKET_NAME,
                        Key=document.filepath,
                    )
                    # Read the file content
                    file_content = await response["Body"].read()
                    logger.info(f"Successfully loaded file from S3: {len(file_content)} bytes")
                    return Response(
                        content=file_content,
                        media_type=media_type,
                        headers={
                            "Content-Disposition": safe_content_disposition(document.filename),
                            "Content-Length": str(len(file_content)),
                        },
                    )
            except Exception as e:
                logger.error(f"Error downloading file from S3: {e}, filepath={document.filepath}")
                raise HTTPException(status_code=404, detail=f"File not found on server: {str(e)}")
        else:
            # File is stored locally
            try:
                # Handle different filepath formats
                if document.filepath.startswith("uploads/"):
                    local_file_path = UPLOADS_DIR / document.filepath.replace("uploads/", "")
                else:
                    # If filepath is just the filename or doesn't have "uploads/" prefix
                    local_file_path = UPLOADS_DIR / document.filepath
                logger.info(f"Attempting to load local file: {local_file_path}, exists={os.path.exists(local_file_path)}")
                if not os.path.exists(local_file_path):
                    logger.error(f"Local file not found: {local_file_path}, filepath from DB: {document.filepath}")
                    raise HTTPException(status_code=404, detail=f"File not found at {local_file_path}")
                with open(local_file_path, "rb") as f:
                    content = f.read()
                logger.info(f"Successfully loaded local file: {len(content)} bytes")
                return Response(
                    content=content,
                    media_type=media_type,
                    headers={
                        "Content-Disposition": safe_content_disposition(document.filename),
                        "Content-Length": str(len(content)),
                    },
                )
            except HTTPException:
                # Re-raise HTTP exceptions (404s) as-is
                raise
            except Exception as e:
                logger.error(f"Error reading local file: {e}, filepath={document.filepath}, local_path={local_file_path}")
                raise HTTPException(status_code=404, detail=f"File not found on server: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download document file")


# -------------------- Annotations API --------------------
@router.post("/annotations", response_model=AnnotationResponse)
async def create_annotation(
    payload: AnnotationCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new annotation for a specific document page with optional text selection.
    
    Args:
        payload: Annotation creation request containing document ID, extraction job UUID, page number,
                text, comment, and optional selection positions.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        AnnotationResponse: Created annotation with UUID, document UUID, extraction job UUID, page number,
                           text, comment, selection positions (if provided), user information, and creation timestamp.
    
    Raises:
        HTTPException: 404 if document or extraction job not found.
        HTTPException: 500 if annotation creation fails.
    """
    try:
        logger.info(f"Creating annotation: document_id={payload.documentId}, job_uuid={payload.extractionJobUuid}, page_number={payload.pageNumber}, user_id={user.id}, has_selection={payload.selectionStart is not None}")
        # Ensure document exists (visible to all users)
        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == payload.documentId, PDFFile.deleted_at.is_(None)
            )
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            logger.warning(f"Document not found for annotation: document_id={payload.documentId}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")

        # Ensure extraction job exists and belongs to the same document
        job_result = await db.execute(
            select(PDFFileExtractionJob).where(
                PDFFileExtractionJob.uuid == payload.extractionJobUuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job or job.pdf_file_uuid != payload.documentId:
            logger.warning(f"Extraction job not found for annotation: job_uuid={payload.extractionJobUuid}, document_id={payload.documentId}, user_id={user.id}")
            raise HTTPException(
                status_code=404, detail="Extraction job not found for document"
            )

        anno_uuid = str(uuid.uuid4())
        anno = PDFFileAnnotation(
            uuid=anno_uuid,
            pdf_file_uuid=payload.documentId,
            extraction_job_uuid=payload.extractionJobUuid,
            page_number=int(payload.pageNumber),
            text=payload.text,
            comment=payload.comment or "",
            selection_start=int(payload.selectionStart),
            selection_end=int(payload.selectionEnd),
            user_id=user.id,
        )
        db.add(anno)
        await db.commit()
        await db.refresh(anno)
        logger.info(f"Created annotation: annotation_uuid={anno_uuid}, document_id={payload.documentId}, page_number={payload.pageNumber}, user_id={user.id}")
        return AnnotationResponse(
            uuid=str(anno.uuid),
            document_uuid=str(anno.pdf_file_uuid),
            extraction_job_uuid=str(anno.extraction_job_uuid),
            page_number=int(anno.page_number),
            text=str(anno.text),
            comment=str(anno.comment),
            selection_start=int(anno.selection_start),
            selection_end=int(anno.selection_end),
            user_id=anno.user_id,
            user_name=anno.user_name,
            created_at=to_utc_isoformat(anno.created_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating annotation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create annotation")


@router.get("/annotations", response_model=List[AnnotationResponse])
async def list_annotations(
    documentId: str,
    extractionJobUuid: str | None = None,
    pageNumber: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List annotations for a document, optionally filtered by extraction job and/or page number.
    
    Args:
        documentId: UUID of the document.
        extractionJobUuid: Optional UUID of extraction job to filter by.
        pageNumber: Optional page number to filter by.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[AnnotationResponse]: List of annotations ordered by creation date (oldest first), each containing
                                  UUID, document UUID, extraction job UUID, page number, text, comment,
                                  selection positions (if available), user information, and creation timestamp.
    
    Raises:
        HTTPException: 404 if document not found.
        HTTPException: 500 if error occurs.
    """
    try:
        logger.info(f"Listing annotations: documentId={documentId}, extractionJobUuid={extractionJobUuid}, pageNumber={pageNumber}, user_id={user.id}")
        # Ensure document exists
        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == documentId, PDFFile.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            logger.warning(f"Document not found for annotation listing: documentId={documentId}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Document not found")

        query = select(PDFFileAnnotation).where(
            PDFFileAnnotation.pdf_file_uuid == documentId, PDFFileAnnotation.deleted_at.is_(None)
        )
        if extractionJobUuid:
            query = query.where(PDFFileAnnotation.extraction_job_uuid == extractionJobUuid)
        if pageNumber is not None:
            query = query.where(PDFFileAnnotation.page_number == pageNumber)
        query = query.order_by(PDFFileAnnotation.created_at.asc())

        result = await db.execute(query)
        annos = result.scalars().all()
        logger.info(f"Found {len(annos)} annotations: documentId={documentId}, extractionJobUuid={extractionJobUuid}, pageNumber={pageNumber}")
        return [
            AnnotationResponse(
                uuid=str(a.uuid),
                document_uuid=str(a.pdf_file_uuid),
                extraction_job_uuid=str(a.extraction_job_uuid),
                page_number=int(a.page_number),
                text=str(a.text),
                comment=str(a.comment),
                selection_start=int(a.selection_start),
                selection_end=int(a.selection_end),
                user_id=a.user_id,
                user_name=a.user_name,
                created_at=to_utc_isoformat(a.created_at),
            )
            for a in annos
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing annotations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list annotations")


@router.delete("/annotations/{annotation_uuid}")
async def delete_annotation(
    annotation_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Soft delete an annotation by UUID.
    
    Args:
        annotation_uuid: UUID of the annotation to delete.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Success message confirming deletion.
    
    Raises:
        HTTPException: 404 if annotation not found.
        HTTPException: 500 if deletion fails.
    """
    logger.info(f"Deleting annotation: annotation_uuid={annotation_uuid}, user_id={user.id}")
    try:
        # Find annotation excluding already deleted ones
        result = await db.execute(
            select(PDFFileAnnotation).where(
                PDFFileAnnotation.uuid == annotation_uuid, PDFFileAnnotation.deleted_at.is_(None)
            )
        )
        anno = result.scalar_one_or_none()
        if not anno:
            logger.warning(f"Annotation not found for deletion: annotation_uuid={annotation_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Annotation not found")

        # Soft delete the annotation
        await db.execute(
            update(PDFFileAnnotation)
            .where(PDFFileAnnotation.uuid == annotation_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await db.commit()
        logger.info(f"Successfully deleted annotation: annotation_uuid={annotation_uuid}, document_uuid={anno.pdf_file_uuid}, page_number={anno.page_number}, user_id={user.id}")
        return {"message": "Annotation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting annotation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete annotation")


@router.post(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs/{job_uuid}/retry",
    response_model=dict,
)
async def retry_extraction_job(
    project_uuid: str,
    document_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry a failed extraction job.
    
    Args:
        project_uuid: UUID of the project.
        document_uuid: UUID of the document.
        job_uuid: UUID of the extraction job to retry.
        db: Database session.
        current_user: Current authenticated user.
    
    Returns:
        dict: Success message with job UUID and status.
    
    Raises:
        HTTPException: 404 if project, document, or extraction job not found.
        HTTPException: 400 if job status is not failed.
        HTTPException: 500 if retry fails.
    """
    logger.info(f"Retrying extraction job: project_uuid={project_uuid}, document_uuid={document_uuid}, job_uuid={job_uuid}, user_id={current_user.id}")
    try:
        # Verify project ownership, excluding deleted projects
        project_result = await db.execute(
            select(PDFProject).where(
                PDFProject.uuid == project_uuid,
                PDFProject.user_id == current_user.id,
                PDFProject.deleted_at.is_(None),
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            logger.warning(f"Project not found for retry: project_uuid={project_uuid}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify document ownership
        doc_result = await db.execute(
            select(PDFFile).where(
                PDFFile.uuid == document_uuid,
                PDFFile.project_uuid == project_uuid,
                PDFFile.deleted_at.is_(None),
            )
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            logger.warning(f"Document not found for retry: document_uuid={document_uuid}, project_uuid={project_uuid}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Document not found")

        # Get the extraction job
        job_result = await db.execute(
            select(PDFFileExtractionJob).where(
                PDFFileExtractionJob.uuid == job_uuid,
                PDFFileExtractionJob.pdf_file_uuid == document_uuid,
                PDFFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(f"Extraction job not found for retry: job_uuid={job_uuid}, document_uuid={document_uuid}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Only allow retry for failed jobs
        if job.status not in [ExtractionStatus.FAILURE, "Failed"]:
            logger.warning(f"Cannot retry job with status: job_uuid={job_uuid}, status={job.status}, user_id={current_user.id}")
            raise HTTPException(
                status_code=400, detail=f"Cannot retry job with status: {job.status}"
            )

        # Reset job status and clear previous results
        job.status = ExtractionStatus.NOT_STARTED
        job.start_time = None
        job.end_time = None
        job.latency_ms = None
        job.cost = None

        # Soft delete existing page content for this job
        await db.execute(
            update(PDFFilePageContent)
            .where(PDFFilePageContent.extraction_job_uuid == job_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )

        await db.commit()
        logger.info(f"Reset job status for retry: job_uuid={job_uuid}, extractor={job.extractor}")

        # Queue the retry task
        try:
            process_document_with_extractor.delay(
                job_uuid, document_uuid, document.filepath, job.extractor
            )
            logger.info(f"Successfully queued retry task: job_uuid={job_uuid}, document_uuid={document_uuid}, extractor={job.extractor}")
        except Exception as task_err:
            logger.error(f"Failed to queue retry task: job_uuid={job_uuid}, error={str(task_err)}")
            # Still return success since the job status was reset
            # The job can be manually retried later

        return {
            "message": "Extraction job retry initiated",
            "job_uuid": job_uuid,
            "status": "NOT_STARTED",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying extraction job: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to retry extraction job: {str(e)}"
        )

