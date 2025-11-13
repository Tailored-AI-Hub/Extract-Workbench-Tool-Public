"""
Image routes for the PDF Extraction Tool API
"""
import uuid
import aioboto3
import json
import math
import os
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timezone

from fastapi import Depends, File, UploadFile, HTTPException, Form, APIRouter
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import joinedload
from loguru import logger

from src.db import get_db
from src.models import (
    ImageProject,
    ImageFile,
    ImageFileExtractionJob,
    ImageContent,
    ImageFeedback,
    ImageAnnotation,
    ImageProjectResponse,
    ImageProjectCreateRequest,
    ImageResponse,
    PaginatedImagesResponse,
    ImageExtractionJobResponse,
    ImageContentResponse,
    ImageFeedbackRequest,
    ImageFeedbackResponse,
    ImageAnnotationCreateRequest,
    ImageAnnotationResponse,
    ImageAnnotationListItem,
    ExtractorInfo,
    ExtractionStatus,
    ImageExtractorType,
    PaginationMeta,
    UserRatingBreakdown,
    User,
)
from src.file_coordinator import register_extraction_tasks
from src.tasks import process_image_with_extractor
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
    get_image_dimensions,
    get_extractor_display_name,
    safe_content_disposition,
)

router = APIRouter()


@router.get("/extractors")
async def get_image_extractors():
    """
    Get list of available image extractors with their metadata and cost information.
    
    Returns:
        dict: Dictionary containing image extractors grouped by category (OCR, Vision),
              with each extractor's ID, name, description, cost per image, and supported tags.
    """
    try:
        logger.info("Fetching available image extractors")
        
        def info(extractor_type: str) -> ExtractorInfo:
            try:
                inst = get_image_reader(extractor_type)
                meta = inst.get_information()
                display_name = meta.get("name", extractor_type)
                
                # Calculate cost per image using CostCalculator
                # Map display names to cost calculator keys for image extractors
                usage_data = {"image_count": 1}
                
                # Special handling for extractors with display name mismatches
                cost_name = display_name
                if display_name == "AWS Textract":
                    # For images, cost calculator uses "Textract Image"
                    cost_name = "Textract Image"
                elif display_name.startswith("OpenAI "):
                    # For vision models, use the extractor_type (gpt-4o-mini, gpt-4o, gpt-5, gpt-5-mini)
                    # which the cost calculator has entries for
                    cost_name = extractor_type
                
                cost_metrics = cost_calculator.calculate_cost(cost_name, usage_data)
                # If still default cost (0.001 is the default for unknown extractors), try extractor_type as fallback
                if abs(cost_metrics.calculated_cost - 0.001) < 0.0001:
                    # For Textract, also try "Textract" directly
                    if extractor_type == "Textract":
                        cost_metrics = cost_calculator.calculate_cost("Textract", usage_data)
                    else:
                        cost_metrics = cost_calculator.calculate_cost(extractor_type, usage_data)
                cost_per_image = cost_metrics.calculated_cost
                
                return ExtractorInfo(
                    id=extractor_type,
                    name=display_name,
                    description=meta.get("description", f"Image extractor {extractor_type}"),
                    cost_per_page=cost_per_image,  # Stored as cost per image for display
                    support_tags=meta.get("supports", ["Text"]),
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

        available = []
        for t in ImageExtractorType:
            available.append(info(t.value))
        
        # Categorize image extractors
        ocr_ids = {"Tesseract", "Textract", "Mathpix", "AzureDI"}
        vision_ids = {"gpt-4o-mini", "gpt-4o", "gpt-5", "gpt-5-mini"}
        
        ocr_extractors = [ext for ext in available if ext.id in ocr_ids]
        vision_extractors = [ext for ext in available if ext.id in vision_ids]
        
        image_extractors = []
        if ocr_extractors:
            image_extractors.append({"category": "OCR", "extractors": ocr_extractors})
        if vision_extractors:
            image_extractors.append({"category": "Vision", "extractors": vision_extractors})
        
        logger.info(f"Found {len(available)} image extractors: OCR={len(ocr_extractors)}, Vision={len(vision_extractors)}")
        return {"image_extractors": image_extractors}
    except Exception as e:
        logger.error(f"Error fetching image extractors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch image extractors")


@router.post("/create-project", response_model=ImageProjectResponse)
async def image_create_project(
    project: ImageProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new image project.
    
    Args:
        project: Project creation request containing name and optional description.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ImageProjectResponse: Created project with UUID, name, description, creation timestamp,
                             owner name, and ownership flag.
    
    Raises:
        HTTPException: 500 if project creation fails.
    """
    try:
        logger.info(f"Creating image project: name={project.name}, user_id={user.id}")
        project_uuid = str(uuid.uuid4())
        new_project = ImageProject(
            uuid=project_uuid,
            name=project.name,
            description=project.description,
            user_id=user.id,
        )
        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)
        logger.info(f"Successfully created image project: uuid={project_uuid}, name={project.name}")
        return ImageProjectResponse(
            uuid=new_project.uuid,
            name=new_project.name,
            description=new_project.description,
            created_at=to_utc_isoformat(new_project.created_at),
            owner_name=new_project.owner_name,
            is_owner=True,
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create image project: user_id={user.id}, name={project.name}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create image project: {str(e)}")


@router.get("/projects", response_model=List[ImageProjectResponse])
async def image_list_projects(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    List all non-deleted image projects, ordered by creation date (newest first).
    
    Args:
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[ImageProjectResponse]: List of image projects with ownership information.
    """
    try:
        logger.info(f"Listing image projects for user_id={user.id}")
        result = await db.execute(
            select(ImageProject)
            .options(joinedload(ImageProject.owner))
            .where(ImageProject.deleted_at.is_(None))
            .order_by(ImageProject.created_at.desc())
        )
        projects = result.scalars().all()
        logger.info(f"Found {len(projects)} image projects")
        return [
            ImageProjectResponse(
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
        logger.error(f"Error listing image projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list image projects")


@router.get("/projects/{project_uuid}", response_model=ImageProjectResponse)
async def image_get_project(project_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Get a specific image project by UUID.
    
    Args:
        project_uuid: UUID of the project to retrieve.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ImageProjectResponse: Project details with ownership information.
    
    Raises:
        HTTPException: 404 if project not found or has been deleted.
    """
    try:
        logger.info(f"Getting image project: project_uuid={project_uuid}, user_id={user.id}")
        result = await db.execute(
            select(ImageProject).options(joinedload(ImageProject.owner)).where(ImageProject.uuid == project_uuid, ImageProject.deleted_at.is_(None))
        )
        p = result.scalar_one_or_none()
        if not p:
            logger.warning(f"Image project not found: project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Project not found")
        return ImageProjectResponse(
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
        logger.error(f"Error getting image project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image project")


@router.delete("/projects/{project_uuid}")
async def delete_image_project(project_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Soft delete an image project and all related data. Only the project owner or admin can delete."""
    try:
        logger.info(f"Deleting image project: project_uuid={project_uuid}, user_id={user.id}")
        # Only the owner (creator) or admin can delete the project
        result = await db.execute(
            select(ImageProject).where(
                ImageProject.uuid == project_uuid, ImageProject.deleted_at.is_(None)
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            logger.warning(f"Image project not found for deletion: project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Project not found")
        is_admin = getattr(user, "role", "user") == "admin"
        if p.user_id != user.id and not is_admin:
            logger.warning(f"Unauthorized project deletion attempt: project_uuid={project_uuid}, user_id={user.id}, owner_id={p.user_id}")
            raise HTTPException(
                status_code=403, detail="Only the project owner or admin can delete this project"
            )

        # Soft delete all related data
        current_time = datetime.now(timezone.utc)

        # Get all images in this project
        images_result = await db.execute(
            select(ImageFile.uuid).where(ImageFile.project_uuid == project_uuid, ImageFile.deleted_at.is_(None))
        )
        image_uuids = [row[0] for row in images_result.all()]

        # Collect job UUIDs for cascading soft deletions
        if image_uuids:
            jobs_result = await db.execute(
                select(ImageFileExtractionJob.uuid).where(
                    ImageFileExtractionJob.image_file_uuid.in_(image_uuids),
                    ImageFileExtractionJob.deleted_at.is_(None),
                )
            )
            job_uuids = [row[0] for row in jobs_result.all()]

            if job_uuids:
                await db.execute(
                    update(ImageContent)
                    .where(ImageContent.extraction_job_uuid.in_(job_uuids))
                    .values(deleted_at=current_time)
                )

            await db.execute(
                update(ImageFeedback)
                .where(ImageFeedback.image_file_uuid.in_(image_uuids))
                .values(deleted_at=current_time)
            )

            await db.execute(
                update(ImageAnnotation)
                .where(ImageAnnotation.image_file_uuid.in_(image_uuids))
                .values(deleted_at=current_time)
            )

            await db.execute(
                update(ImageFileExtractionJob)
                .where(ImageFileExtractionJob.image_file_uuid.in_(image_uuids))
                .values(deleted_at=current_time)
            )

            # Soft delete all images
            await db.execute(
                update(ImageFile)
                .where(ImageFile.project_uuid == project_uuid)
                .values(deleted_at=current_time)
            )

        # Soft delete the project itself
        await db.execute(
            update(ImageProject)
            .where(ImageProject.uuid == project_uuid)
            .values(deleted_at=current_time)
        )

        await db.commit()
        logger.info(f"Successfully deleted image project: project_uuid={project_uuid}, images={len(image_uuids)}, jobs={len(job_uuids) if image_uuids else 0}")
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting image project {project_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.post("/projects/{project_uuid}/upload-multiple")
async def upload_multiple_images(
    project_uuid: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db, use_cache=True),
    user: User = Depends(get_current_user, use_cache=True),
    selected_extractors: str = Form(""),
):
    """
    Upload multiple image files to a project and initiate extraction jobs.
    
    Args:
        project_uuid: UUID of the project to upload files to.
        files: List of image files to upload (supports jpg, jpeg, png, gif, bmp, tiff, tif, webp).
        db: Database session.
        user: Current authenticated user.
        selected_extractors: JSON string of extractor names to use (defaults to Tesseract).
    
    Returns:
        dict: Success message, list of uploaded image UUIDs, and list of failed uploads with errors.
    
    Raises:
        HTTPException: 400 if no files provided or invalid extractor format.
        HTTPException: 404 if project not found.
    """
    try:
        logger.info(f"Uploading {len(files)} image files to project: project_uuid={project_uuid}, user_id={user.id}")
        if not files:
            logger.warning(f"No files provided for upload: project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=400, detail="At least one file is required")
        image_uuids = []
        failed_uploads = []
        try:
            if selected_extractors:
                selected_extractor_list = json.loads(selected_extractors)
            else:
                selected_extractor_list = ["Tesseract"]  # Default extractor
            logger.info(f"Selected extractors: {selected_extractor_list}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid selected_extractors format: {selected_extractors}, error={str(e)}")
            raise HTTPException(status_code=400, detail="Invalid selected_extractors format")
        # Basic project check
        project_result = await db.execute(select(ImageProject).where(ImageProject.uuid == project_uuid, ImageProject.deleted_at.is_(None)))
        if not project_result.scalar_one_or_none():
            logger.warning(f"Project not found for upload: project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Project not found")
        for file in files:
            try:
                if file.filename is None:
                    logger.warning(f"File name is required: filename={file.filename}, user_id={user.id}")
                    failed_uploads.append({"filename": "unknown", "error": "File name is required"})
                    continue
                filename_lower = file.filename.lower()
                if not filename_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp")):
                    failed_uploads.append({"filename": file.filename, "error": "Only image files are allowed"})
                    continue
                image_uuid = str(uuid.uuid4())
                content = await file.read()
                file_size = len(content)
                MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
                if file_size > MAX_UPLOAD_BYTES:
                    logger.warning(f"File too large: filename={file.filename}, size={file_size}, max={MAX_UPLOAD_BYTES}")
                    failed_uploads.append({"filename": file.filename, "error": "File too large (max 20MB)"})
                    continue
                
                # Extract image dimensions
                width, height = get_image_dimensions(content)
                logger.info(f"Processing image file: filename={file.filename}, size={file_size}, dimensions={width}x{height}, image_uuid={image_uuid}")
                
                # Store local or S3
                if is_s3_available():
                    s3_key = f"projects/{project_uuid}/images/{image_uuid}/v1/{file.filename}"
                    logger.info(f"Uploading to S3: key={s3_key}, size={file_size}")
                    session = aioboto3.Session()
                    async with session.client("s3", region_name=AWS_REGION) as s3:
                        await s3.put_object(Bucket=AWS_BUCKET_NAME, Key=s3_key, Body=content)
                    filepath = s3_key
                    logger.info(f"Successfully uploaded to S3: key={s3_key}")
                else:
                    file_path = UPLOADS_DIR / f"{image_uuid}_{file.filename}"
                    logger.info(f"Storing locally: path={file_path}, size={file_size}")
                    with open(file_path, "wb") as buffer:
                        buffer.write(content)
                    filepath = str(Path("uploads") / file_path.name)
                    logger.info(f"Successfully stored locally: path={filepath}")
                image = ImageFile(
                    uuid=image_uuid,
                    filename=file.filename,
                    filepath=filepath,
                    width=width,
                    height=height,
                    project_uuid=project_uuid,
                    user_id=user.id,
                )
                db.add(image)
                image_uuids.append(image_uuid)
                logger.info(f"Added image file to database: image_uuid={image_uuid}, filename={file.filename}")
            except Exception as e:
                logger.error(f"Error processing image file: filename={file.filename}, error={str(e)}")
                failed_uploads.append({"filename": file.filename, "error": f"Error processing file: {str(e)}"})
        await db.commit()
        logger.info(f"Committed {len(image_uuids)} image files to database, {len(failed_uploads)} failed")
        # Create jobs
        total_jobs = 0
        for image_uuid in image_uuids:
            job_uuids = []
            for extractor_name in selected_extractor_list:
                j_uuid = str(uuid.uuid4())
                job = ImageFileExtractionJob(
                    uuid=j_uuid,
                    image_file_uuid=image_uuid,
                    extractor=extractor_name,
                    status=ExtractionStatus.NOT_STARTED,
                )
                db.add(job)
                job_uuids.append(j_uuid)
                total_jobs += 1
            register_extraction_tasks(image_uuid, job_uuids, FILE_CLEANUP_TTL_SECONDS)
            logger.info(f"Created {len(job_uuids)} extraction jobs for image: image_uuid={image_uuid}")
        await db.commit()
        logger.info(f"Created {total_jobs} total extraction jobs")

        # Kick off tasks
        for image_uuid in image_uuids:
            # Fetch path
            result = await db.execute(select(ImageFile).where(ImageFile.uuid == image_uuid))
            img = result.scalar_one()
            # For each job
            jobs_result = await db.execute(select(ImageFileExtractionJob).where(ImageFileExtractionJob.image_file_uuid == image_uuid))
            for job in jobs_result.scalars().all():
                logger.info(f"Queuing extraction task: job_uuid={job.uuid}, image_uuid={image_uuid}, extractor={job.extractor}")
                process_image_with_extractor.delay(job.uuid, image_uuid, img.filepath, job.extractor)

        logger.info(f"Upload complete: project_uuid={project_uuid}, successful={len(image_uuids)}, failed={len(failed_uploads)}, jobs_queued={total_jobs}")
        return {"message": f"Successfully uploaded {len(image_uuids)} files.", "image_uuids": image_uuids, "failed_uploads": failed_uploads}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error uploading image files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload image files")


@router.get("/projects/{project_uuid}/images", response_model=PaginatedImagesResponse)
async def list_project_images(
    project_uuid: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "uploaded_at",
    sort_direction: str = "desc",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List image files in a project with pagination and sorting.
    
    Args:
        project_uuid: UUID of the project.
        page: Page number (default: 1).
        page_size: Number of items per page (default: 10).
        sort_by: Field to sort by (default: uploaded_at).
        sort_direction: Sort direction, 'asc' or 'desc' (default: desc).
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        PaginatedImagesResponse: Paginated list of image files with metadata.
    
    Raises:
        HTTPException: 404 if project not found.
    """
    try:
        logger.info(f"Listing project images: project_uuid={project_uuid}, page={page}, page_size={page_size}, sort_by={sort_by}, sort_direction={sort_direction}")
        # Verify project exists
        project_result = await db.execute(select(ImageProject).where(ImageProject.uuid == project_uuid, ImageProject.deleted_at.is_(None)))
        if not project_result.scalar_one_or_none():
            logger.warning(f"Project not found: project_uuid={project_uuid}")
            raise HTTPException(status_code=404, detail="Project not found")

        # Build query
        query = select(ImageFile).options(joinedload(ImageFile.owner)).where(ImageFile.project_uuid == project_uuid, ImageFile.deleted_at.is_(None))
        
        # Apply sorting
        if sort_by == "uploaded_at":
            order_col = ImageFile.uploaded_at
        elif sort_by == "filename":
            order_col = ImageFile.filename
        else:
            order_col = ImageFile.uploaded_at
        
        if sort_direction == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())
        
        # Get total count
        count_query = select(func.count()).select_from(ImageFile).where(ImageFile.project_uuid == project_uuid, ImageFile.deleted_at.is_(None))
        total_result = await db.execute(count_query)
        total_count = total_result.scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        images = result.scalars().all()
        
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
        logger.info(f"Found {total_count} image files in project, returning page {page} of {total_pages}")
        
        return PaginatedImagesResponse(
            images=[
                ImageResponse(
                    uuid=img.uuid,
                    filename=img.filename,
                    filepath=img.filepath,
                    uploaded_at=to_utc_isoformat(img.uploaded_at),
                    width=img.width,
                    height=img.height,
                    owner_name=img.owner_name,
                )
                for img in images
            ],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_count=total_count,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing project images: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list project images")


@router.get("/projects/{project_uuid}/images/{image_uuid}", response_model=ImageResponse)
async def get_image(project_uuid: str, image_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Get a specific image file by UUID within a project.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ImageResponse: Image file details including UUID, filename, filepath, upload timestamp,
                      dimensions, and owner name.
    
    Raises:
        HTTPException: 404 if image file or project not found.
    """
    try:
        logger.info(f"Getting image file: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
        result = await db.execute(
            select(ImageFile).options(joinedload(ImageFile.owner)).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        img = result.scalar_one_or_none()
        if not img:
            logger.warning(f"Image file not found: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        return ImageResponse(
            uuid=img.uuid,
            filename=img.filename,
            filepath=img.filepath,
            uploaded_at=to_utc_isoformat(img.uploaded_at),
            width=img.width,
            height=img.height,
            owner_name=img.owner_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image")


@router.delete("/projects/{project_uuid}/images/{image_uuid}")
async def delete_image(project_uuid: str, image_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Soft delete an image file and all related data. Only the project owner or admin can delete.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file to delete.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Success message confirming deletion.
    
    Raises:
        HTTPException: 404 if image file or project not found.
        HTTPException: 403 if user is not the project owner or admin.
    """
    try:
        logger.info(f"Deleting image file: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
        # Verify project exists and requester is owner or admin, excluding deleted projects
        project_result = await db.execute(
            select(ImageProject).where(
                ImageProject.uuid == project_uuid, ImageProject.deleted_at.is_(None)
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            logger.warning(f"Project not found for image deletion: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Project not found")
        is_admin = getattr(user, "role", "user") == "admin"
        if project.user_id != user.id and not is_admin:
            logger.warning(f"Unauthorized image deletion attempt: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}, owner_id={project.user_id}")
            raise HTTPException(
                status_code=403, detail="Only the project owner or admin can delete files"
            )
        # Verify image exists in project and is not deleted
        result = await db.execute(
            select(ImageFile).options(joinedload(ImageFile.owner)).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        img = result.scalar_one_or_none()
        if not img:
            logger.warning(f"Image file not found for deletion: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        current_time = datetime.now(timezone.utc)
        
        # Soft delete related data
        jobs_result = await db.execute(
            select(ImageFileExtractionJob.uuid).where(
                ImageFileExtractionJob.image_file_uuid == image_uuid,
                ImageFileExtractionJob.deleted_at.is_(None)
            )
        )
        job_uuids = [row[0] for row in jobs_result.all()]
        logger.info(f"Deleting image file with {len(job_uuids)} related jobs: image_uuid={image_uuid}, filename={img.filename}")
        
        if job_uuids:
            await db.execute(
                update(ImageContent)
                .where(ImageContent.extraction_job_uuid.in_(job_uuids))
                .values(deleted_at=current_time)
            )
        
        await db.execute(
            update(ImageFeedback)
            .where(ImageFeedback.image_file_uuid == image_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(ImageAnnotation)
            .where(ImageAnnotation.image_file_uuid == image_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(ImageFileExtractionJob)
            .where(ImageFileExtractionJob.image_file_uuid == image_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(ImageFile)
            .where(ImageFile.uuid == image_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.commit()
        logger.info(f"Successfully deleted image file: image_uuid={image_uuid}, filename={img.filename}, jobs_deleted={len(job_uuids)}")
        return {"message": "Image deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete image")


@router.get("/projects/{project_uuid}/images/{image_uuid}/extraction-jobs", response_model=List[ImageExtractionJobResponse])
async def get_image_extraction_jobs(
    project_uuid: str,
    image_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all extraction jobs for a specific image file.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[ImageExtractionJobResponse]: List of extraction jobs with status, timing, cost,
                                         and feedback statistics.
    
    Raises:
        HTTPException: 404 if image file not found.
    """
    try:
        logger.info(f"Getting extraction jobs: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
        # Verify image exists in project
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        if not img_result.scalar_one_or_none():
            logger.warning(f"Image file not found: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Get jobs
        jobs_result = await db.execute(
            select(ImageFileExtractionJob)
            .where(
                ImageFileExtractionJob.image_file_uuid == image_uuid,
                ImageFileExtractionJob.deleted_at.is_(None)
            )
            .order_by(ImageFileExtractionJob.start_time.desc().nulls_last())
        )
        jobs = jobs_result.scalars().all()
        logger.info(f"Found {len(jobs)} extraction jobs for image: image_uuid={image_uuid}")
        
        # Get feedback and annotation counts for each job
        jobs_with_stats = []
        for job in jobs:
            # Count annotations
            anno_count_result = await db.execute(
            select(func.count())
            .select_from(ImageAnnotation)
            .where(
                ImageAnnotation.extraction_job_uuid == job.uuid,
                ImageAnnotation.deleted_at.is_(None)
            )
        )
            annotated = anno_count_result.scalar_one() or 0
            
            # Get feedback stats
            feedback_result = await db.execute(
                select(ImageFeedback)
                .where(
                    ImageFeedback.image_file_uuid == image_uuid,
                    ImageFeedback.extraction_job_uuid == job.uuid,
                    ImageFeedback.rating.isnot(None),
                    ImageFeedback.deleted_at.is_(None)
                )
            )
            feedbacks = feedback_result.scalars().all()
            total_feedback_count = len(feedbacks)
            total_rating = None
            if feedbacks:
                ratings = [f.rating for f in feedbacks if f.rating is not None]
                if ratings:
                    total_rating = round(sum(ratings) / len(ratings), 2)
            
            extractor_display_name = get_extractor_display_name(job.extractor, "image")
            jobs_with_stats.append(
                ImageExtractionJobResponse(
                    uuid=job.uuid,
                    image_uuid=job.image_file_uuid,
                    extractor=job.extractor,
                    extractor_display_name=extractor_display_name,
                    status=ExtractionStatus(job.status),
                    start_time=to_utc_isoformat(job.start_time) if job.start_time else None,
                    end_time=to_utc_isoformat(job.end_time) if job.end_time else None,
                    latency_ms=job.latency_ms,
                    cost=job.cost,
                    annotated=annotated,
                    total_rating=total_rating,
                    total_feedback_count=total_feedback_count,
                )
            )
        
        logger.info(f"Returning {len(jobs_with_stats)} extraction job responses: image_uuid={image_uuid}")
        return jobs_with_stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image extraction jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image extraction jobs")


@router.get("/projects/{project_uuid}/images/{image_uuid}/extraction-jobs/{job_uuid}/content", response_model=ImageContentResponse)
async def get_image_extraction_content(
    project_uuid: str,
    image_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get extraction content for a specific image extraction job.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file.
        job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ImageContentResponse: Extraction content with metadata and user feedback if available.
    
    Raises:
        HTTPException: 404 if image file, extraction job, or content not found.
    """
    try:
        logger.info(f"Getting image extraction content: project_uuid={project_uuid}, image_uuid={image_uuid}, job_uuid={job_uuid}, user_id={user.id}")
        # Verify image and job exist
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        if not img_result.scalar_one_or_none():
            logger.warning(f"Image file not found: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        job_result = await db.execute(
            select(ImageFileExtractionJob).where(
                ImageFileExtractionJob.uuid == job_uuid,
                ImageFileExtractionJob.image_file_uuid == image_uuid,
                ImageFileExtractionJob.deleted_at.is_(None)
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(f"Extraction job not found: job_uuid={job_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Extraction job not found")
        
        # Get content
        content_result = await db.execute(
            select(ImageContent).where(
                ImageContent.extraction_job_uuid == job_uuid,
                ImageContent.deleted_at.is_(None)
            )
        )
        content = content_result.scalar_one_or_none()
        if not content:
            logger.warning(f"Content not found: job_uuid={job_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get feedback for this job
        feedback_result = await db.execute(
            select(ImageFeedback).where(
                ImageFeedback.image_file_uuid == image_uuid,
                ImageFeedback.extraction_job_uuid == job_uuid,
                ImageFeedback.user_id == user.id,
                ImageFeedback.deleted_at.is_(None)
            )
        )
        feedback = feedback_result.scalar_one_or_none()
        
        feedback_response = None
        if feedback:
            feedback_response = ImageFeedbackResponse(
                uuid=str(feedback.uuid),
                image_uuid=str(feedback.image_file_uuid),
                extraction_job_uuid=str(feedback.extraction_job_uuid),
                feedback_type=str(feedback.feedback_type),
                rating=feedback.rating,
                comment=feedback.comment,
                user_id=feedback.user_id,
                user_name=user.name,
                created_at=to_utc_isoformat(feedback.created_at),
            )
        
        return ImageContentResponse(
            uuid=content.uuid,
            extraction_job_uuid=content.extraction_job_uuid,
            content=content.content,
            metadata_=content.metadata_ or {},
            feedback=feedback_response,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image extraction content: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image extraction content")


@router.post("/projects/{project_uuid}/images/{image_uuid}/feedback", response_model=ImageFeedbackResponse)
async def submit_image_feedback(
    project_uuid: str,
    image_uuid: str,
    feedback: ImageFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submit or update feedback (rating and/or comment) for a specific image extraction job.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file.
        feedback: Feedback request containing extraction job UUID, rating, and comment.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ImageFeedbackResponse: Created or updated feedback with user information and timestamp.
    
    Raises:
        HTTPException: 404 if image file not found.
    """
    try:
        logger.info(f"Submitting image feedback: project_uuid={project_uuid}, image_uuid={image_uuid}, job_uuid={feedback.extraction_job_uuid}, user_id={user.id}, rating={feedback.rating}")
        # Verify image exists
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == feedback.image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        if not img_result.scalar_one_or_none():
            logger.warning(f"Image not found for feedback: image_uuid={feedback.image_uuid}, project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Upsert per user/job
        existing_q = await db.execute(
            select(ImageFeedback).where(
                ImageFeedback.image_file_uuid == feedback.image_uuid,
                ImageFeedback.extraction_job_uuid == feedback.extraction_job_uuid,
                ImageFeedback.deleted_at.is_(None),
                ImageFeedback.user_id == user.id,
            )
        )
        existing = existing_q.scalar_one_or_none()
        if existing:
            if feedback.rating is not None:
                existing.rating = feedback.rating
            if feedback.comment is not None:
                existing.comment = feedback.comment
            existing.user_id = user.id
            await db.commit()
            logger.info(f"Updated existing feedback: feedback_uuid={existing.uuid}, rating={feedback.rating}")
            return ImageFeedbackResponse(
                uuid=str(existing.uuid),
                image_uuid=str(existing.image_file_uuid),
                extraction_job_uuid=str(existing.extraction_job_uuid),
                feedback_type=str(existing.feedback_type),
                rating=existing.rating,
                comment=existing.comment,
                user_id=existing.user_id,
                user_name=user.name,
                created_at=to_utc_isoformat(existing.created_at),
            )
        
        fb_uuid = str(uuid.uuid4())
        new_fb = ImageFeedback(
            uuid=fb_uuid,
            image_file_uuid=feedback.image_uuid,
            extraction_job_uuid=feedback.extraction_job_uuid,
            feedback_type="single",
            rating=feedback.rating,
            comment=feedback.comment,
            user_id=user.id,
        )
        db.add(new_fb)
        await db.commit()
        await db.refresh(new_fb)
        logger.info(f"Created new feedback: feedback_uuid={fb_uuid}, rating={feedback.rating}")
        return ImageFeedbackResponse(
            uuid=str(new_fb.uuid),
            image_uuid=str(new_fb.image_file_uuid),
            extraction_job_uuid=str(new_fb.extraction_job_uuid),
            feedback_type=str(new_fb.feedback_type),
            rating=new_fb.rating,
            comment=new_fb.comment,
            user_id=new_fb.user_id,
            user_name=user.name,
            created_at=to_utc_isoformat(new_fb.created_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error submitting image feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit image feedback")


@router.get("/projects/{project_uuid}/images/{image_uuid}/feedback", response_model=List[ImageFeedbackResponse])
async def get_image_feedback(
    project_uuid: str,
    image_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all feedback entries for a specific image, ordered by creation date (newest first).
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[ImageFeedbackResponse]: List of feedback entries with ratings, comments, and user information.
    
    Raises:
        HTTPException: 404 if image file not found.
    """
    try:
        logger.info(f"Getting image feedback: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
        # Verify image exists
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        if not img_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Image not found")
        
        result = await db.execute(
            select(ImageFeedback)
            .where(
                ImageFeedback.image_file_uuid == image_uuid,
                ImageFeedback.deleted_at.is_(None)
            )
            .order_by(ImageFeedback.created_at.desc())
        )
        items = result.scalars().all()
        logger.info(f"Found {len(items)} feedback entries for image: image_uuid={image_uuid}")
        
        # Get user names for feedback
        user_ids = {f.user_id for f in items if f.user_id}
        users_map = {}
        if user_ids:
            users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
            users = users_result.scalars().all()
            users_map = {u.id: u.name for u in users}
        
        return [
            ImageFeedbackResponse(
                uuid=str(f.uuid),
                image_uuid=str(f.image_file_uuid),
                extraction_job_uuid=str(f.extraction_job_uuid),
                feedback_type=str(f.feedback_type),
                rating=f.rating,
                comment=f.comment,
                user_id=f.user_id,
                user_name=users_map.get(f.user_id),
                created_at=to_utc_isoformat(f.created_at),
            )
            for f in items
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image feedback")


@router.get("/projects/{project_uuid}/images/{image_uuid}/extraction-jobs/{job_uuid}/average-rating")
async def get_image_average_rating(
    project_uuid: str,
    image_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get average rating for a specific image extraction job, including the current user's rating.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file.
        job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Dictionary containing average_rating (rounded to 2 decimals), total_ratings count,
              and user_rating (current user's rating if available, None otherwise).
              Returns None for average_rating if no ratings exist.
    
    Raises:
        HTTPException: 404 if image file not found.
    """
    try:
        logger.info(f"Getting average rating: project_uuid={project_uuid}, image_uuid={image_uuid}, job_uuid={job_uuid}, user_id={user.id}")
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        if not img_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Image not found")
        
        result = await db.execute(
            select(ImageFeedback).where(
                ImageFeedback.image_file_uuid == image_uuid,
                ImageFeedback.extraction_job_uuid == job_uuid,
                ImageFeedback.rating.isnot(None),
                ImageFeedback.deleted_at.is_(None)
            )
        )
        rows = result.scalars().all()
        if not rows:
            logger.info(f"No ratings found for image: image_uuid={image_uuid}, job_uuid={job_uuid}")
            return {"average_rating": None, "total_ratings": 0, "user_rating": None}
        
        ratings = [r.rating for r in rows if r.rating is not None]
        avg = round(sum(ratings) / len(ratings), 2)
        user_rating = None
        for r in rows:
            if r.user_id == user.id:
                user_rating = r.rating
                break
        
        return {"average_rating": avg, "total_ratings": len(ratings), "user_rating": user_rating}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image average rating: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image average rating")


# User-wise rating breakdown for an image extraction job
@router.get(
    "/projects/{project_uuid}/images/{image_uuid}/extraction-jobs/{job_uuid}/rating-breakdown",
    response_model=List[UserRatingBreakdown],
)
async def get_image_rating_breakdown(
    project_uuid: str,
    image_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get user-wise rating breakdown for an image extraction job"""
    try:
        logger.info(f"Getting rating breakdown: project_uuid={project_uuid}, image_uuid={image_uuid}, job_uuid={job_uuid}, user_id={user.id}")
        # Verify image exists in project
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None),
            )
        )
        if not img_result.scalar_one_or_none():
            logger.warning(f"Image not found for rating breakdown: image_uuid={image_uuid}, project_uuid={project_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")

        # Verify extraction job exists for image
        job_result = await db.execute(
            select(ImageFileExtractionJob).where(
                ImageFileExtractionJob.uuid == job_uuid,
                ImageFileExtractionJob.image_file_uuid == image_uuid,
                ImageFileExtractionJob.deleted_at.is_(None),
            )
        )
        if not job_result.scalar_one_or_none():
            logger.warning(f"Extraction job not found for rating breakdown: job_uuid={job_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Get all feedback for this extraction job, grouped by user
        feedback_result = await db.execute(
            select(ImageFeedback)
            .where(
                ImageFeedback.extraction_job_uuid == job_uuid,
                ImageFeedback.rating.isnot(None),
                ImageFeedback.deleted_at.is_(None),
            )
            .order_by(ImageFeedback.created_at.desc())
        )
        feedbacks = feedback_result.scalars().all()

        # Group by user
        user_feedback_map: Dict[Optional[int], List] = {}
        for fb in feedbacks:
            uid = fb.user_id
            if uid not in user_feedback_map:
                user_feedback_map[uid] = []
            user_feedback_map[uid].append(fb)

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
            latest = user_feedbacks[0]  # Already sorted by created_at desc

            breakdown.append(
                UserRatingBreakdown(
                    user_id=user_id,
                    user_name=user_id_to_name.get(int(user_id)) if user_id is not None else "Unknown User",
                    average_rating=round(avg_rating, 2),
                    pages_rated=1,  # Images don't have pages, so always 1
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
        logger.error(f"Error getting image rating breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get image rating breakdown")


@router.post(
    "/projects/{project_uuid}/images/{image_uuid}/extraction-jobs/{job_uuid}/retry",
    response_model=dict,
)
async def retry_image_extraction_job(
    project_uuid: str,
    image_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed image extraction job"""
    try:
        logger.info(f"Retrying image extraction job: project_uuid={project_uuid}, image_uuid={image_uuid}, job_uuid={job_uuid}, user_id={current_user.id}")
        # Verify project ownership, excluding deleted projects
        project_result = await db.execute(
            select(ImageProject).where(
                ImageProject.uuid == project_uuid,
                ImageProject.user_id == current_user.id,
                ImageProject.deleted_at.is_(None),
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            logger.warning(f"Project not found for retry: project_uuid={project_uuid}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify image ownership
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None),
            )
        )
        image = img_result.scalar_one_or_none()
        if not image:
            logger.warning(f"Image not found for retry: image_uuid={image_uuid}, project_uuid={project_uuid}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Image not found")

        # Get the extraction job
        job_result = await db.execute(
            select(ImageFileExtractionJob).where(
                ImageFileExtractionJob.uuid == job_uuid,
                ImageFileExtractionJob.image_file_uuid == image_uuid,
                ImageFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(f"Extraction job not found for retry: job_uuid={job_uuid}, image_uuid={image_uuid}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Only allow retry for failed jobs
        if job.status not in [ExtractionStatus.FAILURE, "Failed", "Failure"]:
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

        # Soft delete existing content for this job
        await db.execute(
            update(ImageContent)
            .where(ImageContent.extraction_job_uuid == job_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )

        await db.commit()
        logger.info(f"Reset job status for retry: job_uuid={job_uuid}, extractor={job.extractor}")

        # Queue the retry task
        try:
            process_image_with_extractor.delay(
                job_uuid, image_uuid, image.filepath, job.extractor
            )
            logger.info(f"Successfully queued retry task: job_uuid={job_uuid}, image_uuid={image_uuid}, extractor={job.extractor}")
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
        logger.error(f"Error retrying image extraction job: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to retry extraction job: {str(e)}"
        )


@router.post("/annotations", response_model=ImageAnnotationResponse)
async def create_image_annotation(
    payload: ImageAnnotationCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new annotation for a specific image with optional text selection.
    
    Args:
        payload: Annotation creation request containing image ID, extraction job UUID, text, comment,
                and optional selection positions.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        ImageAnnotationResponse: Created annotation with UUID, image UUID, extraction job UUID,
                                text, comment, selection positions (if provided), user information,
                                and creation timestamp.
    
    Raises:
        HTTPException: 404 if image file or extraction job not found.
        HTTPException: 500 if annotation creation fails.
    """
    try:
        logger.info(f"Creating image annotation: image_id={payload.imageId}, job_uuid={payload.extractionJobUuid}, user_id={user.id}, has_selection={payload.selectionStartChar is not None}")
        # Ensure image exists
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == payload.imageId,
                ImageFile.deleted_at.is_(None)
            )
        )
        img = img_result.scalar_one_or_none()
        if not img:
            logger.warning(f"Image not found for annotation: image_id={payload.imageId}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")

        # Ensure extraction job exists and belongs to the same image
        job_result = await db.execute(
            select(ImageFileExtractionJob).where(
                ImageFileExtractionJob.uuid == payload.extractionJobUuid,
                ImageFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job or job.image_file_uuid != payload.imageId:
            logger.warning(f"Extraction job not found for annotation: job_uuid={payload.extractionJobUuid}, image_id={payload.imageId}, user_id={user.id}")
            raise HTTPException(
                status_code=404, detail="Extraction job not found for image"
            )

        anno_uuid = str(uuid.uuid4())
        anno = ImageAnnotation(
            uuid=anno_uuid,
            image_file_uuid=payload.imageId,
            extraction_job_uuid=payload.extractionJobUuid,
            text=payload.text,
            comment=payload.comment or "",
            selection_start_char=payload.selectionStartChar,
            selection_end_char=payload.selectionEndChar,
            user_id=user.id,
        )
        db.add(anno)
        await db.commit()
        await db.refresh(anno)
        logger.info(f"Created image annotation: annotation_uuid={anno_uuid}, image_id={payload.imageId}, user_id={user.id}")
        return ImageAnnotationResponse(
            uuid=str(anno.uuid),
            image_uuid=str(anno.image_file_uuid),
            extraction_job_uuid=str(anno.extraction_job_uuid),
            text=str(anno.text),
            comment=str(anno.comment),
            selection_start_char=anno.selection_start_char,
            selection_end_char=anno.selection_end_char,
            user_id=anno.user_id,
            user_name=anno.user_name,
            created_at=to_utc_isoformat(anno.created_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating image annotation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create image annotation")


@router.get("/annotations")
async def list_image_annotations(
    imageId: str,
    extractionJobUuid: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List annotations for an image file, optionally filtered by extraction job.
    
    Args:
        imageId: UUID of the image file.
        extractionJobUuid: Optional UUID of extraction job to filter by.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        List[ImageAnnotationListItem]: List of annotations ordered by creation date (oldest first),
                                      each containing UUID, image UUID, extraction job UUID, extractor,
                                      text, comment, selection positions (if available), user information,
                                      and creation timestamp.
    
    Raises:
        HTTPException: 404 if image file not found.
        HTTPException: 500 if error occurs.
    """
    try:
        logger.info(f"Listing image annotations: imageId={imageId}, extractionJobUuid={extractionJobUuid}, user_id={user.id}")
        img_result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == imageId,
                ImageFile.deleted_at.is_(None)
            )
        )
        if not img_result.scalar_one_or_none():
            logger.warning(f"Image not found for annotation listing: imageId={imageId}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        query = select(ImageAnnotation).where(
            ImageAnnotation.image_file_uuid == imageId,
            ImageAnnotation.deleted_at.is_(None)
        )
        if extractionJobUuid:
            query = query.where(ImageAnnotation.extraction_job_uuid == extractionJobUuid)
        query = query.order_by(ImageAnnotation.created_at.asc())
        
        result = await db.execute(query)
        rows = result.scalars().all()
        
        # Get extractor names for each annotation
        job_uuids = {a.extraction_job_uuid for a in rows}
        jobs_map = {}
        if job_uuids:
            jobs_result = await db.execute(
                select(ImageFileExtractionJob).where(ImageFileExtractionJob.uuid.in_(job_uuids))
            )
            jobs = jobs_result.scalars().all()
            jobs_map = {j.uuid: j.extractor for j in jobs}
        
        logger.info(f"Found {len(rows)} annotations: imageId={imageId}, extractionJobUuid={extractionJobUuid}")
        return [
            ImageAnnotationListItem(
                uuid=str(a.uuid),
                image_uuid=str(a.image_file_uuid),
                extractor=jobs_map.get(a.extraction_job_uuid, "Unknown"),
                extraction_job_uuid=str(a.extraction_job_uuid),
                user_id=a.user_id,
                user_name=a.user_name,
                text=str(a.text),
                comment=str(a.comment),
                created_at=to_utc_isoformat(a.created_at),
                selection_start_char=a.selection_start_char,
                selection_end_char=a.selection_end_char,
            )
            for a in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image annotations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch annotations: {str(e)}")


@router.delete("/annotations/{annotation_uuid}")
async def delete_image_annotation(
    annotation_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Soft delete an image annotation by UUID.
    
    Args:
        annotation_uuid: UUID of the annotation to delete.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        dict: Success message confirming deletion.
    
    Raises:
        HTTPException: 404 if annotation not found.
    """
    try:
        logger.info(f"Deleting image annotation: annotation_uuid={annotation_uuid}, user_id={user.id}")
        result = await db.execute(
            select(ImageAnnotation).where(
                ImageAnnotation.uuid == annotation_uuid,
                ImageAnnotation.deleted_at.is_(None)
            )
        )
        anno = result.scalar_one_or_none()
        if not anno:
            logger.warning(f"Annotation not found for deletion: annotation_uuid={annotation_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Annotation not found")
        
        await db.execute(
            update(ImageAnnotation)
            .where(ImageAnnotation.uuid == annotation_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await db.commit()
        logger.info(f"Successfully deleted annotation: annotation_uuid={annotation_uuid}, image_uuid={anno.image_file_uuid}, user_id={user.id}")
        return {"message": "Annotation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting image annotation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete image annotation")


@router.get("/projects/{project_uuid}/images/{image_uuid}/image-load")
async def download_image_file(
    project_uuid: str,
    image_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Download an image file from S3 or local storage.
    
    Args:
        project_uuid: UUID of the project.
        image_uuid: UUID of the image file to download.
        db: Database session.
        user: Current authenticated user.
    
    Returns:
        Response: Image file content with appropriate Content-Type and Content-Disposition headers.
    
    Raises:
        HTTPException: 404 if image file not found or file does not exist on server.
    """
    try:
        logger.info(f"Downloading image file: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
        result = await db.execute(
            select(ImageFile).where(
                ImageFile.uuid == image_uuid,
                ImageFile.project_uuid == project_uuid,
                ImageFile.deleted_at.is_(None)
            )
        )
        img = result.scalar_one_or_none()
        if not img:
            logger.warning(f"Image file not found for download: project_uuid={project_uuid}, image_uuid={image_uuid}, user_id={user.id}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Determine media type based on file extension
        filename_lower = img.filename.lower()
        if filename_lower.endswith(('.png',)):
            media_type = "image/png"
        elif filename_lower.endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif filename_lower.endswith(('.gif',)):
            media_type = "image/gif"
        elif filename_lower.endswith(('.webp',)):
            media_type = "image/webp"
        elif filename_lower.endswith(('.bmp',)):
            media_type = "image/bmp"
        elif filename_lower.endswith(('.tiff', '.tif')):
            media_type = "image/tiff"
        else:
            media_type = "image/jpeg"  # default fallback
        
        if img.filepath.startswith("projects/"):
            # File is stored in S3
            try:
                logger.info(f"Downloading from S3: key={img.filepath}, filename={img.filename}")
                session = aioboto3.Session()
                async with session.client("s3", region_name=AWS_REGION) as s3:
                    response = await s3.get_object(Bucket=AWS_BUCKET_NAME, Key=img.filepath)
                    file_content = await response["Body"].read()
                    logger.info(f"Successfully downloaded from S3: key={img.filepath}, size={len(file_content)}")
                    return Response(
                        content=file_content,
                        media_type=media_type,
                        headers={
                            "Content-Disposition": safe_content_disposition(img.filename),
                            "Content-Length": str(len(file_content))
                        }
                    )
            except Exception as e:
                logger.error(f"Error downloading image from S3: key={img.filepath}, error={str(e)}, user_id={user.id}")
                raise HTTPException(status_code=404, detail="File not found on server")
        else:
            # File is stored locally
            try:
                local_file_path = UPLOADS_DIR / img.filepath.replace("uploads/", "")
                logger.info(f"Downloading from local storage: path={local_file_path}, filename={img.filename}")
                if not os.path.exists(local_file_path):
                    logger.warning(f"Local file not found: path={local_file_path}, image_uuid={image_uuid}, user_id={user.id}")
                    raise HTTPException(status_code=404, detail="File not found")
                with open(local_file_path, "rb") as f:
                    content = f.read()
                    logger.info(f"Successfully read local file: path={local_file_path}, size={len(content)}")
                    return Response(
                        content=content,
                        media_type=media_type,
                        headers={
                            "Content-Disposition": safe_content_disposition(img.filename),
                            "Content-Length": str(len(content))
                        }
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error reading local image file: path={local_file_path}, error={str(e)}, user_id={user.id}")
                raise HTTPException(status_code=404, detail="File not found on server")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading image file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download image file")

