"""
Audio routes for the PDF Extraction Tool API
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
    AudioProject,
    AudioFile,
    AudioFileExtractionJob,
    AudioFileContent,
    AudioFileFeedback,
    AudioFileAnnotation,
    AudioProjectResponse,
    AudioProjectCreateRequest,
    AudioResponse,
    PaginatedAudiosResponse,
    AudioExtractionJobResponse,
    AudioSegmentContentResponse,
    AudioSegmentFeedbackRequest,
    AudioSegmentFeedbackResponse,
    ExtractorInfo,
    ExtractionStatus,
    AudioExtractorType,
    PaginationMeta,
    UserRatingBreakdown,
    User,
)
from src.file_coordinator import register_extraction_tasks
from src.tasks import process_audio_with_extractor
from src.factory.audio import get_audio_reader
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
    get_audio_duration,
    get_extractor_display_name,
    safe_content_disposition,
)

router = APIRouter()


@router.get("/extractors")
async def get_audio_extractors():
    """
    Get list of available audio extractors with their metadata and cost information.

    Returns:
        dict: Dictionary containing audio extractors grouped by category (Transcription),
              with each extractor's ID, name, description, cost per minute, and supported tags.
    """

    def info(extractor_type: str) -> ExtractorInfo:
        try:
            inst = get_audio_reader(extractor_type)
            meta = inst.get_information()
            display_name = meta.get("name", extractor_type)

            # Calculate cost per minute using CostCalculator
            # Try display name first, then fallback to extractor_type
            usage_data = {"duration_seconds": 60}
            cost_metrics = cost_calculator.calculate_cost(display_name, usage_data)
            if math.isclose(
                cost_metrics.calculated_cost, 0.001, rel_tol=1e-09, abs_tol=1e-09
            ):  # Default cost, try extractor_type
                cost_metrics = cost_calculator.calculate_cost(
                    extractor_type, usage_data
                )
            cost_per_minute = cost_metrics.calculated_cost

            return ExtractorInfo(
                id=extractor_type,
                name=display_name,
                description=meta.get(
                    "description", f"Audio extractor {extractor_type}"
                ),
                cost_per_page=cost_per_minute,  # Stored as cost per minute for display
                support_tags=meta.get("supports", ["Transcript"]),
            )
        except Exception:
            # Fallback: calculate cost even if get_information fails
            usage_data = {"duration_seconds": 60}
            cost_metrics = cost_calculator.calculate_cost(extractor_type, usage_data)
            cost_per_minute = cost_metrics.calculated_cost

            return ExtractorInfo(
                id=extractor_type,
                name=extractor_type,
                description=f"Audio extractor {extractor_type}",
                cost_per_page=cost_per_minute,
                support_tags=["Transcript"],
            )

    try:
        logger.info("Fetching available audio extractors")
        available = []
        for t in AudioExtractorType:
            available.append(info(t.value))
        logger.info(f"Found {len(available)} audio extractors")
        return {
            "audio_extractors": [{"category": "Transcription", "extractors": available}]
        }
    except Exception as e:
        logger.error(f"Error fetching audio extractors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch audio extractors")


@router.post("/create-project", response_model=AudioProjectResponse)
async def audio_create_project(
    project: AudioProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new audio project.

    Args:
        project: Project creation request containing name and optional description.
        db: Database session.
        user: Current authenticated user.

    Returns:
        AudioProjectResponse: Created project with UUID, name, description, creation timestamp,
                             owner name, and ownership flag.

    Raises:
        HTTPException: 500 if project creation fails.
    """
    try:
        logger.info(f"Creating audio project: name={project.name}, user_id={user.id}")
        project_uuid = str(uuid.uuid4())
        new_project = AudioProject(
            uuid=project_uuid,
            name=project.name,
            description=project.description,
            user_id=user.id,
        )
        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)
        logger.info(
            f"Successfully created audio project: uuid={project_uuid}, name={project.name}"
        )
        return AudioProjectResponse(
            uuid=new_project.uuid,
            name=new_project.name,
            description=new_project.description,
            created_at=to_utc_isoformat(new_project.created_at),
            owner_name=new_project.owner_name,
            is_owner=True,
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Failed to create audio project: user_id={user.id}, name={project.name}, error={str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to create audio project: {str(e)}"
        )


@router.get("/projects", response_model=List[AudioProjectResponse])
async def audio_list_projects(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """
    List all non-deleted audio projects, ordered by creation date (newest first).

    Args:
        db: Database session.
        user: Current authenticated user.

    Returns:
        List[AudioProjectResponse]: List of audio projects with ownership information.
    """
    try:
        logger.info(f"Listing audio projects for user_id={user.id}")
        result = await db.execute(
            select(AudioProject)
            .options(joinedload(AudioProject.owner))
            .where(AudioProject.deleted_at.is_(None))
            .order_by(AudioProject.created_at.desc())
        )
        logger.debug("Fetch Audio Projects Result: ", result)
        projects = result.scalars().all()
        logger.info(f"Found {len(projects)} audio projects")
        return [
            AudioProjectResponse(
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
        logger.error(f"Error listing audio projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list audio projects")


@router.get("/projects/{project_uuid}", response_model=AudioProjectResponse)
async def audio_get_project(
    project_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get a specific audio project by UUID.

    Args:
        project_uuid: UUID of the project to retrieve.
        db: Database session.
        user: Current authenticated user.

    Returns:
        AudioProjectResponse: Project details with ownership information.

    Raises:
        HTTPException: 404 if project not found or has been deleted.
    """
    try:
        logger.info(
            f"Getting audio project: project_uuid={project_uuid}, user_id={user.id}"
        )
        result = await db.execute(
            select(AudioProject).options(joinedload(AudioProject.owner)).where(
                AudioProject.uuid == project_uuid, AudioProject.deleted_at.is_(None)
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            logger.warning(
                f"Audio project not found: project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Project not found")
        return AudioProjectResponse(
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
        logger.error(f"Error getting audio project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audio project")


@router.delete("/projects/{project_uuid}")
async def delete_audio_project(
    project_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft delete an audio project and all related data. Only the project owner can delete."""
    try:
        logger.info(
            f"Deleting audio project: project_uuid={project_uuid}, user_id={user.id}"
        )
        # Only the owner (creator) can delete the project
        result = await db.execute(
            select(AudioProject).where(
                AudioProject.uuid == project_uuid, AudioProject.deleted_at.is_(None)
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            logger.warning(
                f"Audio project not found for deletion: project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Project not found")
        is_admin = getattr(user, "role", "user") == "admin"
        if p.user_id != user.id and not is_admin:
            logger.warning(f"Unauthorized project deletion attempt: project_uuid={project_uuid}, user_id={user.id}, owner_id={p.user_id}")
            raise HTTPException(
                status_code=403, detail="Only the project owner or admin can delete this project"
            )
        # Soft delete all related data
        current_time = datetime.now(timezone.utc)
        # Get all audio files in this project
        audios_result = await db.execute(
            select(AudioFile.uuid).where(
                AudioFile.project_uuid == project_uuid, AudioFile.deleted_at.is_(None)
            )
        )
        audio_uuids = [row[0] for row in audios_result.all()]
        # Collect job UUIDs for cascading soft deletions
        if audio_uuids:
            jobs_result = await db.execute(
                select(AudioFileExtractionJob.uuid).where(
                    AudioFileExtractionJob.audio_file_uuid.in_(audio_uuids),
                    AudioFileExtractionJob.deleted_at.is_(None),
                )
            )
            job_uuids = [row[0] for row in jobs_result.all()]
            if job_uuids:
                await db.execute(
                    update(AudioFileContent)
                    .where(AudioFileContent.extraction_job_uuid.in_(job_uuids))
                    .values(deleted_at=current_time)
                )
            await db.execute(
                update(AudioFileFeedback)
                .where(AudioFileFeedback.audio_file_uuid.in_(audio_uuids))
                .values(deleted_at=current_time)
            )
            await db.execute(
                update(AudioFileAnnotation)
                .where(AudioFileAnnotation.audio_file_uuid.in_(audio_uuids))
                .values(deleted_at=current_time)
            )
            await db.execute(
                update(AudioFileExtractionJob)
                .where(AudioFileExtractionJob.audio_file_uuid.in_(audio_uuids))
                .values(deleted_at=current_time)
            )
            # Soft delete all audio files
            await db.execute(
                update(AudioFile)
                .where(AudioFile.project_uuid == project_uuid)
                .values(deleted_at=current_time)
            )
        # Soft delete the project itself
        await db.execute(
            update(AudioProject)
            .where(AudioProject.uuid == project_uuid)
            .values(deleted_at=current_time)
        )
        await db.commit()
        logger.info(
            f"Successfully deleted audio project: project_uuid={project_uuid}, audio_files={len(audio_uuids)}, jobs={len(job_uuids) if audio_uuids else 0}"
        )
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting audio project {project_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.post("/projects/{project_uuid}/upload-multiple")
async def upload_multiple_audios(
    project_uuid: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db, use_cache=True),
    user: User = Depends(get_current_user, use_cache=True),
    selected_extractors: str = Form(""),
):
    """
    Upload multiple audio files to a project and initiate extraction jobs.

    Args:
        project_uuid: UUID of the project to upload files to.
        files: List of audio files to upload (supports mp3, wav, m4a, flac, ogg, webm).
        db: Database session.
        user: Current authenticated user.
        selected_extractors: JSON string of extractor names to use (defaults to whisper-openai).

    Returns:
        dict: Success message, list of uploaded audio UUIDs, and list of failed uploads with errors.

    Raises:
        HTTPException: 400 if no files provided or invalid extractor format.
        HTTPException: 404 if project not found.
    """
    try:
        logger.info(
            f"Uploading {len(files)} audio files to project: project_uuid={project_uuid}, user_id={user.id}"
        )
        if not files:
            logger.warning(
                f"No files provided for upload: project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=400, detail="At least one file is required")
        audio_uuids = []
        failed_uploads = []
        try:
            if selected_extractors:
                selected_extractor_list = json.loads(selected_extractors)
            else:
                selected_extractor_list = ["whisper-openai"]
            logger.info(f"Selected extractors: {selected_extractor_list}")
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid selected_extractors format: {selected_extractors}, error={str(e)}"
            )
            raise HTTPException(
                status_code=400, detail="Invalid selected_extractors format"
            )

        # Basic project check
        project_result = await db.execute(
            select(AudioProject).where(
                AudioProject.uuid == project_uuid, AudioProject.deleted_at.is_(None)
            )
        )
        if not project_result.scalar_one_or_none():
            logger.warning(
                f"Project not found for upload: project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Project not found")

        for file in files:
            try:
                if file.filename is None:
                    failed_uploads.append(
                        {"filename": "unknown", "error": "File name is required"}
                    )
                    continue
                filename_lower = file.filename.lower()
                if not filename_lower.endswith(
                    (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm")
                ):
                    failed_uploads.append(
                        {
                            "filename": file.filename,
                            "error": "Only audio files are allowed",
                        }
                    )
                    continue
                audio_uuid = str(uuid.uuid4())
                content = await file.read()
                file_size = len(content)
                MAX_UPLOAD_BYTES = 50 * 1024 * 1024
                if file_size > MAX_UPLOAD_BYTES:
                    logger.warning(
                        f"File too large: filename={file.filename}, size={file_size}, max={MAX_UPLOAD_BYTES}"
                    )
                    failed_uploads.append(
                        {
                            "filename": file.filename,
                            "error": "File too large (max 50MB)",
                        }
                    )
                    continue

                # Extract audio duration
                duration_seconds = get_audio_duration(content, file.filename)
                logger.info(
                    f"Processing audio file: filename={file.filename}, size={file_size}, duration={duration_seconds}s, audio_uuid={audio_uuid}"
                )

                # Store local for now (mirroring doc path logic)
                if is_s3_available():
                    s3_key = f"projects/{project_uuid}/audios/{audio_uuid}/v1/{file.filename}"
                    logger.info(f"Uploading to S3: key={s3_key}, size={file_size}")
                    session = aioboto3.Session()
                    async with session.client("s3", region_name=AWS_REGION) as s3:
                        await s3.put_object(
                            Bucket=AWS_BUCKET_NAME, Key=s3_key, Body=content
                        )
                    filepath = s3_key
                    logger.info(f"Successfully uploaded to S3: key={s3_key}")
                else:
                    file_path = UPLOADS_DIR / f"{audio_uuid}_{file.filename}"
                    logger.info(f"Storing locally: path={file_path}, size={file_size}")
                    with open(file_path, "wb") as buffer:
                        buffer.write(content)
                    filepath = str(Path("uploads") / file_path.name)
                    logger.info(f"Successfully stored locally: path={filepath}")

                audio = AudioFile(
                    uuid=audio_uuid,
                    filename=file.filename,
                    filepath=filepath,
                    duration_seconds=duration_seconds,
                    project_uuid=project_uuid,
                    user_id=user.id,
                )
                db.add(audio)
                audio_uuids.append(audio_uuid)
                logger.info(
                    f"Added audio file to database: audio_uuid={audio_uuid}, filename={file.filename}"
                )
            except Exception as e:
                logger.error(
                    f"Error processing audio file: filename={file.filename}, error={str(e)}"
                )
                failed_uploads.append(
                    {
                        "filename": file.filename,
                        "error": f"Error processing file: {str(e)}",
                    }
                )

        await db.commit()
        logger.info(
            f"Committed {len(audio_uuids)} audio files to database, {len(failed_uploads)} failed"
        )

        # Create jobs
        total_jobs = 0
        for audio_uuid in audio_uuids:
            job_uuids = []
            for extractor_name in selected_extractor_list:
                j_uuid = str(uuid.uuid4())
                job = AudioFileExtractionJob(
                    uuid=j_uuid,
                    audio_file_uuid=audio_uuid,
                    extractor=extractor_name,
                    status=ExtractionStatus.NOT_STARTED,
                )
                db.add(job)
                job_uuids.append(j_uuid)
                total_jobs += 1
            register_extraction_tasks(audio_uuid, job_uuids, FILE_CLEANUP_TTL_SECONDS)
            logger.info(
                f"Created {len(job_uuids)} extraction jobs for audio: audio_uuid={audio_uuid}"
            )
        await db.commit()
        logger.info(f"Created {total_jobs} total extraction jobs")

        # Kick off tasks
        for audio_uuid in audio_uuids:
            # Fetch path
            result = await db.execute(
                select(AudioFile).where(AudioFile.uuid == audio_uuid)
            )
            a = result.scalar_one()
            # For each job
            jobs_result = await db.execute(
                select(AudioFileExtractionJob).where(
                    AudioFileExtractionJob.audio_file_uuid == audio_uuid
                )
            )
            for job in jobs_result.scalars().all():
                logger.info(
                    f"Queuing extraction task: job_uuid={job.uuid}, audio_uuid={audio_uuid}, extractor={job.extractor}"
                )
                process_audio_with_extractor.delay(
                    job.uuid, audio_uuid, a.filepath, job.extractor
                )

        logger.info(
            f"Upload complete: project_uuid={project_uuid}, successful={len(audio_uuids)}, failed={len(failed_uploads)}, jobs_queued={total_jobs}"
        )
        return {
            "message": f"Successfully uploaded {len(audio_uuids)} files.",
            "audio_uuids": audio_uuids,
            "failed_uploads": failed_uploads,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error uploading audio files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload audio files")


@router.get("/projects/{project_uuid}/audios", response_model=PaginatedAudiosResponse)
async def list_project_audios(
    project_uuid: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "uploaded_at",
    sort_direction: str = "desc",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List audio files in a project with pagination and sorting.

    Args:
        project_uuid: UUID of the project.
        page: Page number (default: 1).
        page_size: Number of items per page (default: 10).
        sort_by: Field to sort by (default: uploaded_at).
        sort_direction: Sort direction, 'asc' or 'desc' (default: desc).
        db: Database session.
        user: Current authenticated user.

    Returns:
        PaginatedAudiosResponse: Paginated list of audio files with metadata.

    Raises:
        HTTPException: 404 if project not found.
    """
    try:
        logger.info(
            f"Listing project audios: project_uuid={project_uuid}, page={page}, page_size={page_size}, sort_by={sort_by}, sort_direction={sort_direction}"
        )
        project_result = await db.execute(
            select(AudioProject).where(
                AudioProject.uuid == project_uuid, AudioProject.deleted_at.is_(None)
            )
        )
        if not project_result.scalar_one_or_none():
            logger.warning(f"Project not found: project_uuid={project_uuid}")
            raise HTTPException(status_code=404, detail="Project not found")
        count_result = await db.execute(
            select(func.count(AudioFile.uuid)).where(
                AudioFile.project_uuid == project_uuid, AudioFile.deleted_at.is_(None)
            )
        )
        total_count = count_result.scalar()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        logger.info(
            f"Found {total_count} audio files in project, returning page {page} of {total_pages}"
        )
        offset = (page - 1) * page_size
        sort_column = getattr(AudioFile, sort_by)
        order_clause = (
            sort_column.desc() if sort_direction == "desc" else sort_column.asc()
        )
        result = await db.execute(
            select(AudioFile)
            .options(joinedload(AudioFile.owner))  # Load owner relationship to avoid N+1 queries
            .where(
                AudioFile.project_uuid == project_uuid, AudioFile.deleted_at.is_(None)
            )
            .order_by(order_clause)
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        audios = [
            AudioResponse(
                uuid=a.uuid,
                filename=a.filename,
                filepath=a.filepath,
                uploaded_at=to_utc_isoformat(a.uploaded_at),
                duration_seconds=a.duration_seconds,
                owner_name=a.owner_name,
            )
            for a in items
        ]
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
        return PaginatedAudiosResponse(audios=audios, pagination=pagination)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing project audios: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list project audios")


@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}", response_model=AudioResponse
)
async def get_audio(
    project_uuid: str,
    audio_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get a specific audio file by UUID within a project.

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file.
        db: Database session.
        user: Current authenticated user.

    Returns:
        AudioResponse: Audio file details including UUID, filename, filepath, upload timestamp,
                      duration, and owner name.

    Raises:
        HTTPException: 404 if audio file or project not found.
    """
    try:
        logger.info(
            f"Getting audio file: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
        )
        result = await db.execute(
            select(AudioFile).options(joinedload(AudioFile.owner)).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        a = result.scalar_one_or_none()
        if not a:
            logger.warning(
                f"Audio file not found: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        return AudioResponse(
            uuid=a.uuid,
            filename=a.filename,
            filepath=a.filepath,
            uploaded_at=to_utc_isoformat(a.uploaded_at),
            duration_seconds=a.duration_seconds,
            owner_name=a.owner_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audio file")


@router.delete("/projects/{project_uuid}/audios/{audio_uuid}")
async def delete_audio(
    project_uuid: str,
    audio_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft delete an audio file and all related data. Only the project owner can delete."""
    logger.info(
        f"Deleting audio file: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
    )
    # Verify project exists and requester is owner, excluding deleted projects
    project_result = await db.execute(
        select(AudioProject).where(
            AudioProject.uuid == project_uuid, AudioProject.deleted_at.is_(None)
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        logger.warning(
            f"Project not found for audio deletion: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
        )
        raise HTTPException(status_code=404, detail="Project not found")
    is_admin = getattr(user, "role", "user") == "admin"
    if project.user_id != user.id and not is_admin:
        logger.warning(f"Unauthorized audio deletion attempt: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}, owner_id={project.user_id}")
        raise HTTPException(
            status_code=403, detail="Only the project owner or admin can delete files"
        )

    # Fetch audio within project, excluding already deleted audios
    audio_result = await db.execute(
        select(AudioFile).where(
            AudioFile.uuid == audio_uuid,
            AudioFile.project_uuid == project_uuid,
            AudioFile.deleted_at.is_(None),
        )
    )
    audio = audio_result.scalar_one_or_none()
    if not audio:
        logger.warning(
            f"Audio file not found for deletion: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
        )
        raise HTTPException(status_code=404, detail="Audio not found")

    # Collect job UUIDs for cascading soft deletions
    jobs_result = await db.execute(
        select(AudioFileExtractionJob.uuid).where(
            AudioFileExtractionJob.audio_file_uuid == audio_uuid,
            AudioFileExtractionJob.deleted_at.is_(None),
        )
    )
    job_uuid_rows = jobs_result.all()
    job_uuids = [row[0] for row in job_uuid_rows]
    logger.info(
        f"Deleting audio file with {len(job_uuids)} related jobs: audio_uuid={audio_uuid}, filename={audio.filename}"
    )

    try:
        # Soft delete related rows instead of hard delete
        current_time = datetime.now(timezone.utc)

        if job_uuids:
            await db.execute(
                update(AudioFileContent)
                .where(AudioFileContent.extraction_job_uuid.in_(job_uuids))
                .values(deleted_at=current_time)
            )

        await db.execute(
            update(AudioFileFeedback)
            .where(AudioFileFeedback.audio_file_uuid == audio_uuid)
            .values(deleted_at=current_time)
        )

        await db.execute(
            update(AudioFileAnnotation)
            .where(AudioFileAnnotation.audio_file_uuid == audio_uuid)
            .values(deleted_at=current_time)
        )

        await db.execute(
            update(AudioFileExtractionJob)
            .where(AudioFileExtractionJob.audio_file_uuid == audio_uuid)
            .values(deleted_at=current_time)
        )

        # Soft delete the audio itself
        await db.execute(
            update(AudioFile)
            .where(AudioFile.uuid == audio_uuid)
            .values(deleted_at=current_time)
        )

        # Note: We keep the files (S3 and local) for potential recovery
        # Files can be cleaned up later by a separate cleanup job if needed

        await db.commit()
        logger.info(
            f"Successfully deleted audio file: audio_uuid={audio_uuid}, filename={audio.filename}, jobs_deleted={len(job_uuids)}"
        )
        return {"message": "Audio deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting audio {audio_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete audio")


@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}/extraction-jobs",
    response_model=List[AudioExtractionJobResponse],
)
async def get_audio_extraction_jobs(
    project_uuid: str,
    audio_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all extraction jobs for a specific audio file.

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file.
        db: Database session.
        user: Current authenticated user.

    Returns:
        List[AudioExtractionJobResponse]: List of extraction jobs with status, timing, cost,
                                         and feedback statistics.

    Raises:
        HTTPException: 404 if audio file not found.
    """
    try:
        logger.info(
            f"Getting extraction jobs: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
        )
        # Verify audio exists
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio file not found: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        result = await db.execute(
            select(AudioFileExtractionJob)
            .where(
                AudioFileExtractionJob.audio_file_uuid == audio_uuid,
                AudioFileExtractionJob.deleted_at.is_(None),
            )
            .order_by(AudioFileExtractionJob.extractor)
        )
        jobs = result.scalars().all()
        logger.info(
            f"Found {len(jobs)} extraction jobs for audio: audio_uuid={audio_uuid}"
        )
        responses = []
        for job in jobs:
            # Get all feedback for this extraction job
            try:
                feedback_query = select(AudioFileFeedback).where(
                    AudioFileFeedback.extraction_job_uuid == job.uuid,
                    AudioFileFeedback.deleted_at.is_(None),
                )
                feedback_result = await db.execute(feedback_query)
                feedbacks = feedback_result.scalars().all()

                # Calculate statistics
                total_feedback_count = len(feedbacks)
                segments_annotated = len(
                    set(f.segment_number for f in feedbacks if f.rating is not None)
                )

                # Calculate average rating (safely get rating if it exists)
                ratings = [f.rating for f in feedbacks if f.rating is not None]
                total_rating = (
                    round(sum(ratings) / len(ratings), 2) if ratings else None
                )
            except Exception as e:
                # If schema doesn't support ratings yet, use defaults
                logger.warning(f"Could not fetch feedback stats: {e}")
                total_feedback_count = 0
                segments_annotated = 0
                total_rating = None

            # Safely convert status to enum
            try:
                job_status = ExtractionStatus(job.status)
            except (ValueError, KeyError):
                # Handle legacy status values or invalid status
                job_status = ExtractionStatus.NOT_STARTED

            extractor_display_name = get_extractor_display_name(job.extractor, "audio")
            responses.append(
                AudioExtractionJobResponse(
                    uuid=job.uuid,
                    audio_uuid=job.audio_file_uuid,
                    extractor=job.extractor,
                    extractor_display_name=extractor_display_name,
                    status=job_status,
                    start_time=to_utc_isoformat(job.start_time)
                    if job.start_time
                    else None,
                    end_time=to_utc_isoformat(job.end_time) if job.end_time else None,
                    latency_ms=int(job.latency_ms or 0),
                    cost=float(job.cost or 0.0),
                    segments_annotated=segments_annotated,
                    total_rating=total_rating,
                    total_feedback_count=total_feedback_count,
                )
            )
        logger.info(
            f"Returning {len(responses)} extraction job responses: audio_uuid={audio_uuid}"
        )
        return responses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio extraction jobs: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to get audio extraction jobs"
        )


@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}/extraction-jobs/{job_uuid}/segments"
)
async def get_audio_segments(
    project_uuid: str,
    audio_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all segments (transcription chunks) for a specific extraction job.

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file.
        job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.

    Returns:
        List: List of audio segments with timing information and content. Format varies by extractor:
              - whisper-openai: Uses 'start' and 'end' fields (in seconds).
              - Other extractors: Uses 'start_ms' and 'end_ms' fields (in milliseconds).

    Raises:
        HTTPException: 404 if extraction job or audio file not found.
    """
    try:
        logger.info(
            f"Getting audio segments: project_uuid={project_uuid}, audio_uuid={audio_uuid}, job_uuid={job_uuid}, user_id={user.id}"
        )
        # Verify
        job_result = await db.execute(
            select(AudioFileExtractionJob).where(
                AudioFileExtractionJob.uuid == job_uuid,
                AudioFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(
                f"Extraction job not found: job_uuid={job_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Extraction job not found")
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio file not found: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        result = await db.execute(
            select(AudioFileContent)
            .where(
                AudioFileContent.extraction_job_uuid == job_uuid,
                AudioFileContent.deleted_at.is_(None),
            )
            .order_by(AudioFileContent.segment_number)
        )
        segments = result.scalars().all()
        logger.info(
            f"Found {len(segments)} segments for job: job_uuid={job_uuid}, extractor={job.extractor}"
        )

        # Check extractor type to determine field names
        extractor_type = job.extractor

        # For whisper-openai, use start/end instead of start_ms/end_ms
        if extractor_type == "whisper-openai":
            return [
                {
                    "uuid": str(s.uuid),
                    "extraction_job_uuid": str(s.extraction_job_uuid),
                    "segment_number": s.segment_number,
                    "start": s.start_ms,  # Renamed from start_ms to start
                    "end": s.end_ms,  # Renamed from end_ms to end
                    "content": s.content if s.content is not None else {},
                    "feedback": None,  # Add if needed
                }
                for s in segments
            ]
        else:
            return [
                AudioSegmentContentResponse(
                    uuid=str(s.uuid),
                    extraction_job_uuid=str(s.extraction_job_uuid),
                    segment_number=s.segment_number,
                    start_ms=s.start_ms,
                    end_ms=s.end_ms,
                    content=s.content if s.content is not None else {},
                    feedback=None,
                )
                for s in segments
            ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio segments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audio segments")


@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}/extraction-jobs/{job_uuid}/raw-result"
)
async def get_audio_extraction_raw_result(
    project_uuid: str,
    audio_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get raw extraction result for supported extractors (AWS Transcribe, AssemblyAI).
    Returns the full raw transcript data in the original format.
    """
    try:
        logger.info(
            f"Getting raw extraction result: project_uuid={project_uuid}, audio_uuid={audio_uuid}, job_uuid={job_uuid}, user_id={user.id}"
        )
        # Verify job exists
        job_result = await db.execute(
            select(AudioFileExtractionJob).where(
                AudioFileExtractionJob.uuid == job_uuid,
                AudioFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(
                f"Extraction job not found for raw result: job_uuid={job_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Verify audio exists
        audio_result = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not audio_result.scalar_one_or_none():
            logger.warning(
                f"Audio file not found for raw result: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")

        # Check if extractor is supported
        supported_extractors = ["aws-transcribe", "assemblyai"]
        if job.extractor not in supported_extractors:
            logger.warning(
                f"Unsupported extractor for raw result: extractor={job.extractor}, job_uuid={job_uuid}, user_id={user.id}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Raw result is only available for {', '.join(supported_extractors)} extractors",
            )

        # Get the first segment which should contain the raw transcript data
        segment_result = await db.execute(
            select(AudioFileContent)
            .where(
                AudioFileContent.extraction_job_uuid == job_uuid,
                AudioFileContent.deleted_at.is_(None),
            )
            .order_by(AudioFileContent.segment_number)
            .limit(1)
        )
        first_segment = segment_result.scalar_one_or_none()

        if not first_segment:
            logger.warning(
                f"No segments found for raw result: job_uuid={job_uuid}, extractor={job.extractor}"
            )
            raise HTTPException(
                status_code=404, detail="No segments found for this extraction job"
            )

        if not first_segment.metadata_:
            logger.warning(
                f"Empty metadata for raw result: job_uuid={job_uuid}, segment_number={first_segment.segment_number}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Raw transcript data not found. Metadata is empty for segment {first_segment.segment_number}",
            )

        # Handle different extractors
        if job.extractor == "aws-transcribe":
            logger.info(f"Returning AWS Transcribe raw result: job_uuid={job_uuid}")
            raw_transcript_data = first_segment.metadata_.get("raw_transcript_data")
            if not raw_transcript_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Raw transcript data not found in metadata. Available keys: {list(first_segment.metadata_.keys())}",
                )

            # Format response for AWS Transcribe
            return {
                "uuid": first_segment.uuid,
                "extraction_job_uuid": job_uuid,
                "results": raw_transcript_data.get("results", {}),
                "status": "COMPLETED"
                if job.status == ExtractionStatus.SUCCESS
                else "FAILED",
            }

        elif job.extractor == "assemblyai":
            raw_transcript_json = first_segment.metadata_.get("raw_transcript_json")
            if not raw_transcript_json:
                # Provide more detailed error message
                available_keys = (
                    list(first_segment.metadata_.keys())
                    if first_segment.metadata_
                    else []
                )
                logger.warning(
                    f"Raw transcript JSON not found: job_uuid={job_uuid}, available_keys={available_keys}"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Raw transcript JSON not found in metadata. Available keys: {available_keys}. "
                    f"Segment number: {first_segment.segment_number}, "
                    f"Extractor in metadata: {first_segment.metadata_.get('extractor', 'not found')}",
                )

            logger.info(f"Returning AssemblyAI raw result: job_uuid={job_uuid}")
            # Return the raw AssemblyAI transcript JSON
            return {
                "uuid": first_segment.uuid,
                "extraction_job_uuid": job_uuid,
                **raw_transcript_json,  # Include all fields from raw_transcript_json (text, words, entities, etc.)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio extraction raw result: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to get audio extraction raw result"
        )


@router.post(
    "/projects/{project_uuid}/audios/{audio_uuid}/extraction-jobs/{job_uuid}/retry",
    response_model=dict,
)
async def retry_audio_extraction_job(
    project_uuid: str,
    audio_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed audio extraction job"""
    try:
        logger.info(
            f"Retrying audio extraction job: project_uuid={project_uuid}, audio_uuid={audio_uuid}, job_uuid={job_uuid}, user_id={current_user.id}"
        )
        # Verify project ownership, excluding deleted projects
        project_result = await db.execute(
            select(AudioProject).where(
                AudioProject.uuid == project_uuid,
                AudioProject.user_id == current_user.id,
                AudioProject.deleted_at.is_(None),
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            logger.warning(
                f"Project not found for retry: project_uuid={project_uuid}, user_id={current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify audio ownership
        audio_result = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        audio = audio_result.scalar_one_or_none()
        if not audio:
            logger.warning(
                f"Audio not found for retry: audio_uuid={audio_uuid}, project_uuid={project_uuid}, user_id={current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")

        # Get the extraction job
        job_result = await db.execute(
            select(AudioFileExtractionJob).where(
                AudioFileExtractionJob.uuid == job_uuid,
                AudioFileExtractionJob.audio_file_uuid == audio_uuid,
                AudioFileExtractionJob.deleted_at.is_(None),
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            logger.warning(
                f"Extraction job not found for retry: job_uuid={job_uuid}, audio_uuid={audio_uuid}, user_id={current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Only allow retry for failed jobs
        if job.status not in [ExtractionStatus.FAILURE, "Failed", "Failure"]:
            logger.warning(
                f"Cannot retry job with status: job_uuid={job_uuid}, status={job.status}, user_id={current_user.id}"
            )
            raise HTTPException(
                status_code=400, detail=f"Cannot retry job with status: {job.status}"
            )

        # Reset job status and clear previous results
        job.status = ExtractionStatus.NOT_STARTED
        job.start_time = None
        job.end_time = None
        job.latency_ms = None
        job.cost = None

        # Soft delete existing segment content for this job
        await db.execute(
            update(AudioFileContent)
            .where(AudioFileContent.extraction_job_uuid == job_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )

        await db.commit()
        logger.info(
            f"Reset job status for retry: job_uuid={job_uuid}, extractor={job.extractor}"
        )

        # Queue the retry task
        try:
            process_audio_with_extractor.delay(
                job_uuid, audio_uuid, audio.filepath, job.extractor
            )
            logger.info(
                f"Successfully queued retry task: job_uuid={job_uuid}, audio_uuid={audio_uuid}, extractor={job.extractor}"
            )
        except Exception as task_err:
            logger.error(
                f"Failed to queue retry task: job_uuid={job_uuid}, error={str(task_err)}"
            )
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
        logger.error(f"Error retrying audio extraction job: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to retry extraction job: {str(e)}"
        )


@router.post(
    "/projects/{project_uuid}/audios/{audio_uuid}/feedback",
    response_model=AudioSegmentFeedbackResponse,
)
async def submit_audio_feedback(
    project_uuid: str,
    audio_uuid: str,
    feedback: AudioSegmentFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submit or update feedback (rating and/or comment) for a specific audio segment.

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file.
        feedback: Feedback request containing segment number, extraction job UUID, rating, and comment.
        db: Database session.
        user: Current authenticated user.

    Returns:
        AudioSegmentFeedbackResponse: Created or updated feedback with user information and timestamp.

    Raises:
        HTTPException: 404 if audio file not found.
    """
    try:
        logger.info(
            f"Submitting audio feedback: project_uuid={project_uuid}, audio_uuid={audio_uuid}, segment_number={feedback.segment_number}, job_uuid={feedback.extraction_job_uuid}, user_id={user.id}, rating={feedback.rating}"
        )
        # Verify audio exists
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == feedback.audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio not found for feedback: audio_uuid={feedback.audio_uuid}, project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        # Upsert per user/segment/job
        existing_q = await db.execute(
            select(AudioFileFeedback).where(
                AudioFileFeedback.audio_file_uuid == feedback.audio_uuid,
                AudioFileFeedback.segment_number == feedback.segment_number,
                AudioFileFeedback.extraction_job_uuid == feedback.extraction_job_uuid,
                AudioFileFeedback.deleted_at.is_(None),
                AudioFileFeedback.user_id == user.id,
            )
        )
        existing = existing_q.scalar_one_or_none()
        if existing:
            if feedback.rating is not None:
                existing.rating = feedback.rating
            if feedback.comment is not None:
                existing.comment = feedback.comment
            existing.user_id = user.id
            # Do not set existing.user_name (column does not exist on model)
            await db.commit()
            logger.info(
                f"Updated existing feedback: feedback_uuid={existing.uuid}, segment_number={feedback.segment_number}, rating={feedback.rating}"
            )
            return AudioSegmentFeedbackResponse(
                uuid=str(existing.uuid),
                audio_uuid=str(existing.audio_file_uuid),
                segment_number=int(existing.segment_number),
                extraction_job_uuid=str(existing.extraction_job_uuid),
                feedback_type=str(existing.feedback_type),
                rating=existing.rating,
                comment=existing.comment,
                user_id=existing.user_id,
                user_name=user.name,
                created_at=to_utc_isoformat(existing.created_at),
            )
        fb_uuid = str(uuid.uuid4())
        new_fb = AudioFileFeedback(
            uuid=fb_uuid,
            audio_file_uuid=feedback.audio_uuid,
            segment_number=feedback.segment_number,
            extraction_job_uuid=feedback.extraction_job_uuid,
            feedback_type="single",
            rating=feedback.rating,
            comment=feedback.comment,
            user_id=user.id,
        )
        db.add(new_fb)
        await db.commit()
        await db.refresh(new_fb)
        logger.info(
            f"Created new feedback: feedback_uuid={fb_uuid}, segment_number={feedback.segment_number}, rating={feedback.rating}"
        )
        return AudioSegmentFeedbackResponse(
            uuid=str(new_fb.uuid),
            audio_uuid=str(new_fb.audio_file_uuid),
            segment_number=int(new_fb.segment_number),
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
        logger.error(f"Error submitting audio feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit audio feedback")


@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}/segments/{segment_number}/feedback",
    response_model=List[AudioSegmentFeedbackResponse],
)
async def get_audio_segment_feedback(
    project_uuid: str,
    audio_uuid: str,
    segment_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get all feedback entries for a specific audio segment, ordered by creation date (newest first).

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file.
        segment_number: Segment number to get feedback for.
        db: Database session.
        user: Current authenticated user.

    Returns:
        List[AudioSegmentFeedbackResponse]: List of feedback entries with ratings, comments, and user information.

    Raises:
        HTTPException: 404 if audio file not found.
    """
    try:
        logger.info(
            f"Getting segment feedback: project_uuid={project_uuid}, audio_uuid={audio_uuid}, segment_number={segment_number}, user_id={user.id}"
        )
        # Verify audio exists
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio not found for feedback retrieval: audio_uuid={audio_uuid}, project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        result = await db.execute(
            select(AudioFileFeedback)
            .where(
                AudioFileFeedback.audio_file_uuid == audio_uuid,
                AudioFileFeedback.segment_number == segment_number,
                AudioFileFeedback.deleted_at.is_(None),
            )
            .order_by(AudioFileFeedback.created_at.desc())
        )
        items = result.scalars().all()
        logger.info(
            f"Found {len(items)} feedback entries for segment: audio_uuid={audio_uuid}, segment_number={segment_number}"
        )
        return [
            AudioSegmentFeedbackResponse(
                uuid=str(f.uuid),
                audio_uuid=str(f.audio_file_uuid),
                segment_number=int(f.segment_number),
                extraction_job_uuid=str(f.extraction_job_uuid),
                feedback_type=str(f.feedback_type),
                rating=f.rating,
                comment=f.comment,
                user_id=f.user_id,
                user_name=None,
                created_at=to_utc_isoformat(f.created_at),
            )
            for f in items
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio segment feedback: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to get audio segment feedback"
        )


@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}/segments/{segment_number}/average-rating"
)
async def get_audio_segment_average_rating(
    project_uuid: str,
    audio_uuid: str,
    segment_number: int,
    extraction_job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get average rating for a specific audio segment from a specific extraction job, including the current user's rating.

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file.
        segment_number: Segment number to get average rating for.
        extraction_job_uuid: UUID of the extraction job.
        db: Database session.
        user: Current authenticated user.

    Returns:
        dict: Dictionary containing average_rating (rounded to 2 decimals), total_ratings count,
              and user_rating (current user's rating if available, None otherwise).
              Returns None for average_rating if no ratings exist.

    Raises:
        HTTPException: 404 if audio file not found.
    """
    try:
        logger.info(
            f"Getting average rating: project_uuid={project_uuid}, audio_uuid={audio_uuid}, segment_number={segment_number}, job_uuid={extraction_job_uuid}, user_id={user.id}"
        )
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio not found for average rating: audio_uuid={audio_uuid}, project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        result = await db.execute(
            select(AudioFileFeedback).where(
                AudioFileFeedback.audio_file_uuid == audio_uuid,
                AudioFileFeedback.segment_number == segment_number,
                AudioFileFeedback.extraction_job_uuid == extraction_job_uuid,
                AudioFileFeedback.rating.isnot(None),
                AudioFileFeedback.deleted_at.is_(None),
            )
        )
        rows = result.scalars().all()
        if not rows:
            logger.info(
                f"No ratings found for segment: audio_uuid={audio_uuid}, segment_number={segment_number}, job_uuid={extraction_job_uuid}"
            )
            return {"average_rating": None, "total_ratings": 0, "user_rating": None}
        ratings = [r.rating for r in rows if r.rating is not None]
        avg = round(sum(ratings) / len(ratings), 2)
        user_rating = None
        for r in rows:
            if r.user_id == user.id:
                user_rating = r.rating
                break
        return {
            "average_rating": avg,
            "total_ratings": len(ratings),
            "user_rating": user_rating,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio segment average rating: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to get audio segment average rating"
        )


# User-wise rating breakdown for an audio extraction job
@router.get(
    "/projects/{project_uuid}/audios/{audio_uuid}/extraction-jobs/{job_uuid}/rating-breakdown",
    response_model=List[UserRatingBreakdown],
)
async def get_audio_rating_breakdown(
    project_uuid: str,
    audio_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get user-wise rating breakdown for an audio extraction job"""
    try:
        logger.info(
            f"Getting rating breakdown: project_uuid={project_uuid}, audio_uuid={audio_uuid}, job_uuid={job_uuid}, user_id={user.id}"
        )
        # Verify audio exists in project
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio not found for rating breakdown: audio_uuid={audio_uuid}, project_uuid={project_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")

        # Verify extraction job exists for audio
        jres = await db.execute(
            select(AudioFileExtractionJob).where(
                AudioFileExtractionJob.uuid == job_uuid,
                AudioFileExtractionJob.audio_file_uuid == audio_uuid,
                AudioFileExtractionJob.deleted_at.is_(None),
            )
        )
        if not jres.scalar_one_or_none():
            logger.warning(
                f"Extraction job not found for rating breakdown: job_uuid={job_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Get all feedback for this extraction job, grouped by user
        fres = await db.execute(
            select(AudioFileFeedback)
            .where(
                AudioFileFeedback.extraction_job_uuid == job_uuid,
                AudioFileFeedback.deleted_at.is_(None),
            )
            .order_by(AudioFileFeedback.created_at.desc())
        )
        feedbacks = fres.scalars().all()

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
            users_result = await db.execute(
                select(User.id, User.name).where(User.id.in_(user_ids))
            )
            for uid, name in users_result.all():
                user_id_to_name[int(uid)] = name

        breakdown = []
        for uid, u_feedbacks in user_feedback_map.items():
            ratings = [f.rating for f in u_feedbacks if f.rating is not None]
            if not ratings:
                continue
            avg_rating = sum(ratings) / len(ratings)
            segments_rated = len(set(f.segment_number for f in u_feedbacks))
            latest = u_feedbacks[0]  # sorted desc by created_at
            breakdown.append(
                UserRatingBreakdown(
                    user_id=uid,
                    user_name=user_id_to_name.get(int(uid))
                    if uid is not None
                    else "Unknown User",
                    average_rating=round(avg_rating, 2),
                    pages_rated=segments_rated,  # reuse field name
                    total_ratings=len(ratings),
                    latest_comment=latest.comment,
                    latest_rated_at=to_utc_isoformat(latest.created_at),
                )
            )

        logger.info(
            f"Returning rating breakdown: job_uuid={job_uuid}, users={len(breakdown)}, total_feedbacks={len(feedbacks)}"
        )
        return breakdown
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio rating breakdown: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to get audio rating breakdown"
        )


# Audio annotations
@router.post("/annotations")
async def create_audio_annotation(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new annotation for a specific audio segment with optional text selection.

    Args:
        payload: Dictionary containing:
            - audioId: UUID of the audio file.
            - extractionJobUuid: UUID of the extraction job.
            - segmentNumber: Segment number to annotate.
            - text: Text content of the annotation.
            - comment: Optional comment for the annotation.
            - selectionStartChar: Optional start character position of text selection.
            - selectionEndChar: Optional end character position of text selection.
        db: Database session.
        user: Current authenticated user.

    Returns:
        dict: Created annotation with UUID, audio UUID, segment number, text, comment,
              selection positions (if provided), user information, and creation timestamp.

    Raises:
        HTTPException: 404 if audio file or extraction job not found.
        HTTPException: 500 if annotation creation fails.
    """
    try:
        audio_id = payload.get("audioId")
        extraction_job_uuid = payload.get("extractionJobUuid")
        segment_number = int(payload.get("segmentNumber"))
        text = payload.get("text")
        comment = payload.get("comment") or ""
        selection_start_char = payload.get("selectionStartChar")
        selection_end_char = payload.get("selectionEndChar")
        logger.info(
            f"Creating audio annotation: audio_id={audio_id}, job_uuid={extraction_job_uuid}, segment_number={segment_number}, user_id={user.id}, has_selection={selection_start_char is not None}"
        )

        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_id, AudioFile.deleted_at.is_(None)
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio not found for annotation: audio_id={audio_id}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        jobres = await db.execute(
            select(AudioFileExtractionJob).where(
                AudioFileExtractionJob.uuid == extraction_job_uuid,
                AudioFileExtractionJob.deleted_at.is_(None),
            )
        )
        if not jobres.scalar_one_or_none():
            logger.warning(
                f"Extraction job not found for annotation: job_uuid={extraction_job_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Extraction job not found")

        anno_uuid = str(uuid.uuid4())
        anno = AudioFileAnnotation(
            uuid=anno_uuid,
            audio_file_uuid=audio_id,
            extraction_job_uuid=extraction_job_uuid,
            segment_number=segment_number,
            text=text,
            comment=comment,
            selection_start_char=selection_start_char,
            selection_end_char=selection_end_char,
            user_id=user.id,
        )
        db.add(anno)
        await db.commit()
        await db.refresh(anno)
        logger.info(
            f"Created audio annotation: annotation_uuid={anno_uuid}, audio_id={audio_id}, segment_number={segment_number}, user_id={user.id}"
        )
        response = {
            "uuid": str(anno.uuid),
            "audio_uuid": str(anno.audio_file_uuid),
            "extraction_job_uuid": str(anno.extraction_job_uuid),
            "segment_number": int(anno.segment_number),
            "text": str(anno.text),
            "comment": str(anno.comment),
            "user_id": anno.user_id,
            "user_name": anno.user_name,
            "created_at": to_utc_isoformat(anno.created_at),
        }
        # Only include selection fields if they are not None
        if anno.selection_start_char is not None:
            response["selection_start_char"] = anno.selection_start_char
        if anno.selection_end_char is not None:
            response["selection_end_char"] = anno.selection_end_char
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating audio annotation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create audio annotation")


@router.get("/annotations")
async def list_audio_annotations(
    audioId: str,
    extractionJobUuid: str | None = None,
    segmentNumber: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List annotations for an audio file, optionally filtered by extraction job and/or segment number.

    Args:
        audioId: UUID of the audio file.
        extractionJobUuid: Optional UUID of extraction job to filter by.
        segmentNumber: Optional segment number to filter by.
        db: Database session.
        user: Current authenticated user.

    Returns:
        List[dict]: List of annotations ordered by creation date (oldest first), each containing
                   UUID, audio UUID, extraction job UUID, segment number, text, comment,
                   selection positions (if available), user information, and creation timestamp.

    Raises:
        HTTPException: 404 if audio file not found.
        HTTPException: 500 if database schema mismatch or other error occurs.
    """
    try:
        logger.info(
            f"Listing audio annotations: audioId={audioId}, extractionJobUuid={extractionJobUuid}, segmentNumber={segmentNumber}, user_id={user.id}"
        )
        ares = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audioId, AudioFile.deleted_at.is_(None)
            )
        )
        if not ares.scalar_one_or_none():
            logger.warning(
                f"Audio not found for annotation listing: audioId={audioId}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")

        query = select(AudioFileAnnotation).where(
            AudioFileAnnotation.audio_file_uuid == audioId,
            AudioFileAnnotation.deleted_at.is_(None),
        )
        if extractionJobUuid:
            query = query.where(
                AudioFileAnnotation.extraction_job_uuid == extractionJobUuid
            )
        if segmentNumber is not None:
            query = query.where(AudioFileAnnotation.segment_number == segmentNumber)
        query = query.order_by(AudioFileAnnotation.created_at.asc())

        result = await db.execute(query)
        rows = result.scalars().all()
        results = []
        for a in rows:
            result = {
                "uuid": str(a.uuid),
                "audio_uuid": str(a.audio_file_uuid),
                "extraction_job_uuid": str(a.extraction_job_uuid),
                "segment_number": int(a.segment_number),
                "text": str(a.text),
                "comment": str(a.comment),
                "user_id": a.user_id,
                "user_name": a.user_name,
                "created_at": to_utc_isoformat(a.created_at),
            }
            # Only include selection fields if they are not None
            # Handle both old column names (selection_start_ms/selection_end_ms) and new ones (selection_start_char/selection_end_char)
            try:
                selection_start = getattr(a, "selection_start_char", None)
                if selection_start is None:
                    # Fallback to old column name for backward compatibility
                    selection_start = getattr(a, "selection_start_ms", None)
                if selection_start is not None:
                    result["selection_start_char"] = selection_start
            except (AttributeError, KeyError):
                pass

            try:
                selection_end = getattr(a, "selection_end_char", None)
                if selection_end is None:
                    # Fallback to old column name for backward compatibility
                    selection_end = getattr(a, "selection_end_ms", None)
                if selection_end is not None:
                    result["selection_end_char"] = selection_end
            except (AttributeError, KeyError):
                pass

            results.append(result)
        logger.info(
            f"Found {len(results)} annotations: audioId={audioId}, extractionJobUuid={extractionJobUuid}, segmentNumber={segmentNumber}"
        )
        return results
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"Error fetching audio annotations: {error_detail}")
        # Check if error is related to missing columns - suggest migration
        error_str = str(e).lower()
        if (
            "selection_start" in error_str
            or "selection_end" in error_str
            or "no such column" in error_str
        ):
            raise HTTPException(
                status_code=500,
                detail=f"Database schema mismatch. Please restart the backend server or run the migration script: migrate_audio_annotations.py. Error: {str(e)}",
            )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch annotations: {str(e)}"
        )


@router.delete("/annotations/{annotation_uuid}")
async def delete_audio_annotation(
    annotation_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Soft delete an audio annotation by UUID.

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
        logger.info(
            f"Deleting audio annotation: annotation_uuid={annotation_uuid}, user_id={user.id}"
        )
        result = await db.execute(
            select(AudioFileAnnotation).where(
                AudioFileAnnotation.uuid == annotation_uuid,
                AudioFileAnnotation.deleted_at.is_(None),
            )
        )
        anno = result.scalar_one_or_none()
        if not anno:
            logger.warning(
                f"Annotation not found for deletion: annotation_uuid={annotation_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Annotation not found")
        await db.execute(
            update(AudioFileAnnotation)
            .where(AudioFileAnnotation.uuid == annotation_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await db.commit()
        logger.info(
            f"Successfully deleted annotation: annotation_uuid={annotation_uuid}, audio_uuid={anno.audio_file_uuid}, user_id={user.id}"
        )
        return {"message": "Annotation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting audio annotation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete audio annotation")


@router.get("/projects/{project_uuid}/audios/{audio_uuid}/audio-load")
async def download_audio_file(
    project_uuid: str,
    audio_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Download an audio file from S3 or local storage.

    Args:
        project_uuid: UUID of the project.
        audio_uuid: UUID of the audio file to download.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Response: Audio file content with appropriate Content-Type and Content-Disposition headers.

    Raises:
        HTTPException: 404 if audio file not found or file does not exist on server.
    """
    try:
        logger.info(
            f"Downloading audio file: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
        )
        result = await db.execute(
            select(AudioFile).where(
                AudioFile.uuid == audio_uuid,
                AudioFile.project_uuid == project_uuid,
                AudioFile.deleted_at.is_(None),
            )
        )
        audio = result.scalar_one_or_none()
        if not audio:
            logger.warning(
                f"Audio file not found for download: project_uuid={project_uuid}, audio_uuid={audio_uuid}, user_id={user.id}"
            )
            raise HTTPException(status_code=404, detail="Audio not found")
        if audio.filepath.startswith("projects/"):
            try:
                logger.info(
                    f"Downloading from S3: key={audio.filepath}, filename={audio.filename}"
                )
                session = aioboto3.Session()
                async with session.client("s3", region_name=AWS_REGION) as s3:
                    response = await s3.get_object(
                        Bucket=AWS_BUCKET_NAME, Key=audio.filepath
                    )
                    file_content = await response["Body"].read()
                    logger.info(
                        f"Successfully downloaded from S3: key={audio.filepath}, size={len(file_content)}"
                    )
                    return Response(
                        content=file_content,
                        media_type="audio/mpeg",
                        headers={
                            "Content-Disposition": safe_content_disposition(
                                audio.filename
                            ),
                            "Content-Length": str(len(file_content)),
                        },
                    )
            except Exception as e:
                logger.error(
                    f"Error downloading audio from S3: key={audio.filepath}, error={str(e)}, user_id={user.id}"
                )
                raise HTTPException(status_code=404, detail="File not found on server")
        else:
            try:
                local_file_path = UPLOADS_DIR / audio.filepath.replace("uploads/", "")
                logger.info(
                    f"Downloading from local storage: path={local_file_path}, filename={audio.filename}"
                )
                if not os.path.exists(local_file_path):
                    logger.warning(
                        f"Local file not found: path={local_file_path}, audio_uuid={audio_uuid}, user_id={user.id}"
                    )
                    raise HTTPException(status_code=404, detail="File not found")
                with open(local_file_path, "rb") as f:
                    content = f.read()
                    logger.info(
                        f"Successfully read local file: path={local_file_path}, size={len(content)}"
                    )
                    return Response(
                        content=content,
                        media_type="audio/mpeg",
                        headers={
                            "Content-Disposition": safe_content_disposition(
                                audio.filename
                            ),
                            "Content-Length": str(len(content)),
                        },
                    )
            except Exception as e:
                logger.error(
                    f"Error reading local audio file: path={local_file_path}, error={str(e)}, user_id={user.id}"
                )
                raise HTTPException(status_code=404, detail="File not found on server")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading audio file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download audio file")
