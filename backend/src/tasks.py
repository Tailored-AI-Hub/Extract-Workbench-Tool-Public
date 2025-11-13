import os
import time
import uuid
from celery import Celery
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from loguru import logger
from contextlib import contextmanager
from datetime import datetime, timezone
from src.constants import (
    EXTRACTOR_RETRY_CONFIG,
    DEFAULT_RETRY_CONFIG,
    REDIS_BROKER_URL,
    REDIS_BACKEND_URL,
    DATABASE_URL,
    CIRCUIT_BREAKER_THRESHOLD,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
)
from src.cost_calculator import cost_calculator
from src.file_coordinator import (
    download_to_shared_volume,
    mark_task_complete,
    mark_task_failed,
    redis_client,
)
from sqlalchemy.exc import DatabaseError, OperationalError, PendingRollbackError
from psycopg2 import DatabaseError as Psycopg2DatabaseError
from src.factory.pdf import get_reader
from src.factory.audio import get_audio_reader
from src.factory.image import get_image_reader
from src.models.database import PDFFile, PDFFileExtractionJob, PDFFilePageContent, AudioFile, AudioFileExtractionJob, AudioFileContent, ImageFile, ImageFileExtractionJob, ImageContent
from src.models import AudioExtractionJob, AudioSegmentContent, Audio, ImageExtractionJob, Image  # Use aliases for backward compatibility
from src.models.enums import ExtractionStatus

# Configure Celery
celery_app = Celery("pdf_extraction")
celery_app.config_from_object(
    {
        "broker_url": REDIS_BROKER_URL,
        "result_backend": REDIS_BACKEND_URL,
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
    }
)

# Create synchronous database engine for Celery tasks
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Get database session for Celery tasks"""
    return SessionLocal()


@contextmanager
def get_db_session_context():
    """Get database session with automatic cleanup and rollback for Celery tasks"""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        # Rollback transaction on any error
        try:
            session.rollback()
            logger.debug("Transaction rolled back after error")
        except Exception as rollback_err:
            logger.warning(f"Error during rollback: {rollback_err}")
        raise
    finally:
        try:
            session.close()
            logger.debug("Database session closed successfully")
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")
        # DO NOT dispose engine here - it's shared across all tasks


def calculate_extraction_cost(extractor_type: str, page_count: int) -> float:
    """Calculate cost based on extractor type and page count"""
    # Cost per page for different extractors (example rates)
    cost_per_page = {
        # PDF extractors - Free Python-based extractors
        "PyPDF2": 0.0,  # Free Python PDF library
        "PyMuPDF": 0.0,  # Free Python PDF library
        "PDFPlumber": 0.0,  # Free Python PDF library
        # "Camelot": 0.0,  # Disabled - causing failures
        "MarkItDown": 0.0,  # Free Python markdown conversion library
        
        # Third-party API extractors
        "LlamaParse": 0.003,  # LlamaParse API pricing (estimated)
        "Mathpix": 0.004,  # Mathpix API pricing (estimated)
        
        # AWS services
        "Textract": 0.0015,  # AWS Textract pricing
        
        # OCR extractors
        "Tesseract": 0.0,  # Free OCR
        
        # OpenAI Vision models
        "gpt-4o-mini": 0.005,  # OpenAI GPT-4o-mini pricing
        "gpt-4o": 0.010,  # OpenAI GPT-4o pricing
        "gpt-5": 0.020,  # OpenAI GPT-5 pricing
        "gpt-5-mini": 0.008,  # OpenAI GPT-5-mini pricing
    }
    base_cost = cost_per_page.get(extractor_type, 0.001)
    return round(base_cost * page_count, 4)


def get_retry_config(extractor_type: str) -> dict:
    """Get retry configuration based on extractor type"""
    return EXTRACTOR_RETRY_CONFIG.get(extractor_type, DEFAULT_RETRY_CONFIG)


def is_infrastructure_error(exception: Exception) -> bool:
    """Determine if error is infrastructure-related (don't retry)"""
    infrastructure_errors = (
        DatabaseError,
        OperationalError,
        PendingRollbackError,  # Add this
        Psycopg2DatabaseError,
        ConnectionError,
        FileNotFoundError,
        OSError,
    )
    return isinstance(exception, infrastructure_errors)


def check_circuit_breaker(extractor_type: str) -> bool:
    """Check if circuit breaker is open for this extractor"""
    circuit_key = f"circuit_breaker:{extractor_type}"
    failure_count = redis_client.get(circuit_key)
    if failure_count and int(failure_count) >= CIRCUIT_BREAKER_THRESHOLD:
        logger.warning(f"Circuit breaker OPEN for {extractor_type} - too many failures")
        return True
    return False


def record_extractor_failure(extractor_type: str):
    """Record failure for circuit breaker tracking"""
    from .file_coordinator import redis_client
    from .constants import CIRCUIT_BREAKER_TIMEOUT
    circuit_key = f"circuit_breaker:{extractor_type}"
    redis_client.incr(circuit_key)
    redis_client.expire(circuit_key, CIRCUIT_BREAKER_TIMEOUT)


def reset_circuit_breaker(extractor_type: str):
    """Reset circuit breaker on success"""
    from .file_coordinator import redis_client
    circuit_key = f"circuit_breaker:{extractor_type}"
    redis_client.delete(circuit_key)


@celery_app.task(bind=True)
def process_document_with_extractor(
    self, job_uuid: str, document_uuid: str, file_path: str, extractor_type: str
):
    """
    Process a document with the specified extractor (sync or async).
    """
    start_time = datetime.now(timezone.utc)
    temp_file_path = None
    with get_db_session_context() as db:
        try:
            # Check circuit breaker before processing
            if check_circuit_breaker(extractor_type):
                raise RuntimeError(
                    f"Circuit breaker is OPEN for {extractor_type}. "
                    f"Too many recent failures. Try again later."
                )
            # Update job status to Processing
            db.execute(
                update(PDFFileExtractionJob)
                .where(PDFFileExtractionJob.uuid == job_uuid)
                .values(status=ExtractionStatus.PROCESSING, start_time=start_time)
            )
            db.commit()
            # --- 1. Conditional file retrieval based on storage type ---
            local_file_path = None
            temp_file_path = None
            # Get document info from database to determine storage type
            # Use query() method for better session management
            document = db.query(PDFFile).filter(PDFFile.uuid == document_uuid).first()
            if not document:
                raise RuntimeError(f"Document {document_uuid} not found")
            # Check if file is stored in S3 (starts with "projects/") or locally
            if file_path.startswith("projects/"):
                # Use shared volume coordination for S3 files
                shared_path = download_to_shared_volume(
                    document_uuid, file_path, document.filename
                )
                local_file_path = shared_path
                temp_file_path = None  # Don't track as temp (managed by coordinator)
                logger.info(f"Using shared volume file: {shared_path}")
            elif os.path.exists(file_path):
                # File is stored locally
                logger.info(f"Using existing local file: {file_path}")
                local_file_path = file_path
            else:
                # File not found in either location
                raise RuntimeError(f"File not found: {file_path}")
            # --- 2. Get the right reader ---
            reader = get_reader(extractor_type)  # from your factory.py
            # --- 3. Start extraction ---
            result_or_job_id = reader.read(local_file_path, document_uuid=document_uuid)
            # --- 3. Handle sync vs async ---
            if reader.supports_webhook():
                # You would normally not poll here; webhook handler will call back later
                # For Celery job, you might just exit early and let webhook handler finish DB update
                page_contents = None
            else:
                if isinstance(result_or_job_id, dict):  # sync reader returned results
                    page_contents = result_or_job_id
                else:
                    job_id = result_or_job_id
                    # Poll until job finishes with timeout
                    max_polling_time = 1800  # 30 minutes max polling time
                    poll_interval = 5  # Poll every 5 seconds
                    start_poll_time = time.time()
                    status = reader.get_status(job_id)
                    
                    while status not in ["succeeded", "failed"]:
                        elapsed_time = time.time() - start_poll_time
                        if elapsed_time >= max_polling_time:
                            raise RuntimeError(
                                f"Extraction job {job_id} timed out after {max_polling_time} seconds. "
                                f"Last status: {status}"
                            )
                        logger.info(
                            f"Job {job_id} status: {status}, retrying... "
                            f"(elapsed: {int(elapsed_time)}s / {max_polling_time}s)"
                        )
                        time.sleep(poll_interval)
                        status = reader.get_status(job_id)
                    
                    if status == "failed":
                        raise RuntimeError(f"Extraction failed for job {job_id}")
                    page_contents = reader.get_result(job_id)
            # --- 4. Validate and save page contents to DB ---
            def _has_meaningful_content(pages):
                try:
                    if not pages:
                        return False
                    for _p, body in pages.items():
                        data = (body or {}).get("content", {})
                        # Check for various content types that extractors might return
                        text = (
                            data.get("COMBINED")
                            or data.get("TEXT")
                            or data.get("LATEX")
                            or data.get("MARKDOWN")  # For MarkItDown
                            or data.get("TABLE")  # For PDFPlumber tables
                            or ""
                        ).strip()
                        if text:
                            return True
                    return False
                except Exception:
                    return False
            if not _has_meaningful_content(page_contents):
                raise RuntimeError(
                    f"No meaningful content extracted by {extractor_type}"
                )
            if page_contents:
                try:
                    print(
                        f"Extractor {extractor_type} produced {len(page_contents)} pages; sample keys: {list(next(iter(page_contents.values())).get('content', {}).keys()) if page_contents else []}"
                    )
                except Exception:
                    pass
                for page_num, content in page_contents.items():
                    page_content = PDFFilePageContent(
                        pdf_file_uuid=document_uuid,
                        uuid=str(uuid.uuid4()),
                        extraction_job_uuid=job_uuid,
                        page_number=page_num,
                        content=content["content"],
                    )
                    db.add(page_content)
            # --- 5. Calculate cost using new cost calculator ---
            page_count = len(page_contents) if page_contents else 0
            
            logger.info(f"🧮 [COST CALCULATION] Starting cost calculation for {extractor_type}")
            logger.info(f"🧮 [COST CALCULATION] Page count: {page_count}")
            logger.info(f"🧮 [COST CALCULATION] Page contents keys: {list(page_contents.keys()) if page_contents else []}")
            
            # Extract API response for cost calculation if available
            api_response = None
            if isinstance(result_or_job_id, dict) and "_api_response" in result_or_job_id:
                api_response = result_or_job_id["_api_response"]
                logger.info(f"🧮 [COST CALCULATION] API response found: {type(api_response)}")
            else:
                logger.info(f"🧮 [COST CALCULATION] No API response found, result type: {type(result_or_job_id)}")
            
            usage_data = {"page_count": page_count}
            logger.info(f"🧮 [COST CALCULATION] Usage data: {usage_data}")
            
            cost_metrics = cost_calculator.calculate_cost(
                extractor_name=extractor_type,
                usage_data=usage_data,
                api_response=api_response
            )
            
            logger.info(f"🧮 [COST CALCULATION] Cost metrics result: {cost_metrics}")
            logger.info(f"🧮 [COST CALCULATION] Calculated cost: ${cost_metrics.calculated_cost:.6f}")
            logger.info(f"🧮 [COST CALCULATION] Actual cost: ${cost_metrics.actual_cost if cost_metrics.actual_cost else 'N/A'}")
            
            # Track usage in Langfuse if available
            logger.info(f"📊 [LANGFUSE] Tracking usage for {extractor_type}")
            try:
                cost_calculator.track_usage(
                    extractor_name=extractor_type,
                    usage_data=usage_data,
                    cost_metrics=cost_metrics,
                    trace_id=job_uuid
                )
                logger.info(f"📊 [LANGFUSE] Usage tracking completed successfully")
            except Exception as e:
                logger.warning(f"📊 [LANGFUSE] Usage tracking failed: {e}")

            # --- 6. Latency & cost ---
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(f"💾 [DATABASE] Updating job {job_uuid} with cost: ${cost_metrics.calculated_cost:.6f}")
            
            db.execute(
                update(PDFFileExtractionJob)
                .where(PDFFileExtractionJob.uuid == job_uuid)
                .values(
                    status=ExtractionStatus.SUCCESS,
                    end_time=end_time,
                    latency_ms=latency_ms,
                    cost=cost_metrics.calculated_cost,
                )
            )
            
            logger.info(f"💾 [DATABASE] Job update executed successfully")
            db.commit()
            logger.info(
                f"Successfully processed document {document_uuid} with {extractor_type}"
            )
            # Reset circuit breaker on success
            reset_circuit_breaker(extractor_type)
            # Mark task complete and cleanup if needed
            mark_task_complete(document_uuid, job_uuid)
        except Exception as e:
            # Failure path
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            # CRITICAL: Rollback any pending transaction before attempting failure update
            try:
                db.rollback()
                logger.debug("Transaction rolled back in exception handler")
            except Exception as rb_err:
                logger.warning(f"Error rolling back transaction: {rb_err}")
            # Attempt to update job status to FAILURE
            try:
                db.execute(
                    update(PDFFileExtractionJob)
                    .where(PDFFileExtractionJob.uuid == job_uuid)
                    .values(
                        status=ExtractionStatus.FAILURE,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        cost=0.0,
                    )
                )
                db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update job status to FAILURE: {db_err}")
                # Continue with failure handling even if DB update fails
            # Record failure for circuit breaker
            record_extractor_failure(extractor_type)
            # Check if infrastructure error - fail immediately
            if is_infrastructure_error(e):
                logger.error(
                    f"Infrastructure failure for {extractor_type} - NOT RETRYING: {str(e)}"
                )
                mark_task_failed(document_uuid, job_uuid)
                raise  # Don't retry infrastructure errors
            logger.error(
                f"Failed to process document {document_uuid} with {extractor_type}: {str(e)}"
            )
            logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, "__cause__"):
                logger.error(
                    f"Caused by: {type(e.__cause__).__name__}: {str(e.__cause__)}"
                )
            mark_task_failed(document_uuid, job_uuid)
            # Get extractor-specific retry config
            retry_config = get_retry_config(extractor_type)
            raise self.retry(
                exc=e,
                countdown=retry_config["countdown"],
                max_retries=retry_config["max_retries"],
            )
        finally:
            # Note: Shared volume files are managed by file_coordinator
            # Only cleanup temp files from old S3 download logic
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {temp_file_path}: {e}"
                    )


@celery_app.task(bind=True)
def process_audio_with_extractor(
    self, job_uuid: str, audio_uuid: str, file_path: str, extractor_type: str
):
    """
    Process an audio file with the specified extractor.
    """
    start_time = datetime.now(timezone.utc)
    # Initialize duration_seconds before try block to avoid UnboundLocalError
    duration_seconds = 0
    api_response = None
    
    with get_db_session_context() as db:
        try:
            # Update job status to Processing
            db.execute(
                update(AudioExtractionJob)
                .where(AudioExtractionJob.uuid == job_uuid)
                .values(status=ExtractionStatus.PROCESSING, start_time=start_time)
            )
            db.commit()

            # Resolve file path (S3 vs local)
            local_file_path = None
            audio = db.query(Audio).filter(Audio.uuid == audio_uuid).first()
            if not audio:
                raise RuntimeError(f"Audio {audio_uuid} not found")
            if file_path.startswith("projects/"):
                shared_path = download_to_shared_volume(audio_uuid, file_path, audio.filename)
                local_file_path = shared_path
            elif os.path.exists(file_path):
                local_file_path = file_path
            else:
                raise RuntimeError(f"File not found: {file_path}")

            # Get audio reader and read
            reader = get_audio_reader(extractor_type)
            
            # Try to get duration from extractor's get_usage_metrics method first (most accurate)
            try:
                usage_metrics = reader.get_usage_metrics(local_file_path)
                if usage_metrics and "duration_seconds" in usage_metrics:
                    duration_seconds = usage_metrics["duration_seconds"]
                    logger.info(f"📊 [DURATION] Got duration from get_usage_metrics: {duration_seconds}s")
            except Exception as e:
                logger.warning(f"📊 [DURATION] Could not get duration from get_usage_metrics: {e}")
            
            result = reader.read(local_file_path)
            
            # Extract duration for cost calculation (fallback if get_usage_metrics didn't work)
            segments = result
            
            # If duration is still 0, try to calculate from segments
            if duration_seconds == 0:
                if isinstance(result, dict):
                    # Check if any segment has duration info
                    max_end_ms = 0
                    for seg_num, content in result.items():
                        if isinstance(content, dict):
                            # Look for duration in various formats
                            if "duration" in content:
                                duration_seconds = max(duration_seconds, content["duration"])
                            # Check for Whisper format (flat structure with start/end in milliseconds)
                            elif "end" in content and "start" in content:
                                # start and end are already in milliseconds for Whisper
                                segment_end_ms = max(content.get("end", 0), content.get("start", 0))
                                max_end_ms = max(max_end_ms, segment_end_ms)
                            # Check for AssemblyAI/AWS Transcribe format (nested structure with metadata)
                            elif "metadata" in content:
                                metadata = content.get("metadata", {})
                                # Check for start_ms and end_ms in metadata
                                if "end_ms" in metadata and metadata["end_ms"] is not None:
                                    max_end_ms = max(max_end_ms, metadata["end_ms"])
                                elif "start_ms" in metadata and metadata["start_ms"] is not None:
                                    max_end_ms = max(max_end_ms, metadata["start_ms"])
                    
                    # Convert max_end_ms to seconds if we found timestamps
                    if max_end_ms > 0:
                        duration_seconds = max_end_ms / 1000.0
                        logger.info(f"📊 [DURATION] Calculated duration from segments: {duration_seconds}s (max_end_ms: {max_end_ms})")
                    
                    # Check if result contains API response with cost info
                    if isinstance(result, dict) and "_api_response" in result:
                        api_response = result["_api_response"]
                else:
                    # If result is not a dict, it might be a simple string or other format
                    # For now, assume default duration
                    if duration_seconds == 0:
                        duration_seconds = 60  # Default 1 minute if we can't determine
                        logger.warning(f"📊 [DURATION] Using default duration: {duration_seconds}s")
            
            logger.info(f"📊 [DURATION] Final duration for cost calculation: {duration_seconds}s")

            # Save segments
            if isinstance(segments, dict):
                for seg_num, content in segments.items():
                    # Handle new whisper format (flat structure) vs old format (nested structure)
                    if "text" in content and "start" in content:
                        # New whisper format: flat structure with text, start, end
                        # Store in format compatible with AWS/Assembly (COMBINED and TEXT)
                        whisper_text = content.get("text", "")
                        seg = AudioSegmentContent(
                            uuid=str(uuid.uuid4()),
                            audio_file_uuid=audio_uuid,
                            extraction_job_uuid=job_uuid,
                            segment_number=int(seg_num),
                            start_ms=content.get("start"),
                            end_ms=content.get("end"),
                            content={
                                "text": whisper_text,
                                "TEXT": whisper_text,
                                "COMBINED": whisper_text,
                            },
                        )
                        # Store other fields as metadata
                        metadata = {k: v for k, v in content.items() if k not in ["text", "start", "end"]}
                        # Round confidence if present in metadata
                        if metadata and "confidence" in metadata:
                            from src.extractor.audio.utils import round_confidence
                            metadata["confidence"] = round_confidence(metadata["confidence"])
                        if metadata:
                            seg.metadata_ = metadata
                        seg.metadata_ = seg.metadata_ or {}
                        seg.metadata_["extractor"] = extractor_type
                        db.add(seg)
                    else:
                        # Old format: nested structure with content and metadata
                        metadata = content.get("metadata", {})
                        # Round confidence if present in metadata
                        if metadata and "confidence" in metadata:
                            from src.extractor.audio.utils import round_confidence
                            metadata["confidence"] = round_confidence(metadata["confidence"])
                        seg = AudioSegmentContent(
                            uuid=str(uuid.uuid4()),
                            audio_file_uuid=audio_uuid,
                            extraction_job_uuid=job_uuid,
                            segment_number=int(seg_num),
                            start_ms=metadata.get("start_ms"),
                            end_ms=metadata.get("end_ms"),
                            content=content.get("content", {}),
                        )
                        # Store metadata if present (e.g., raw_transcript_data for AWS Transcribe)
                        if metadata:
                            seg.metadata_ = metadata
                        db.add(seg) 
 
            # Calculate cost using the new cost calculator
            usage_data = {"duration_seconds": duration_seconds}
            cost_metrics = cost_calculator.calculate_cost(
                extractor_name=extractor_type,
                usage_data=usage_data,
                api_response=api_response
            )
            
            # Track usage in Langfuse if available
            cost_calculator.track_usage(
                extractor_name=extractor_type,
                usage_data=usage_data,
                cost_metrics=cost_metrics,
                trace_id=job_uuid
            )
 
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            db.execute(
                update(AudioExtractionJob)
                .where(AudioExtractionJob.uuid == job_uuid)
                .values(
                    status=ExtractionStatus.SUCCESS,
                    end_time=end_time,
                    latency_ms=latency_ms,
                    cost=cost_metrics.calculated_cost,
                )
            )
            db.commit()
            mark_task_complete(audio_uuid, job_uuid)
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            try:
                db.rollback()
            except Exception:
                pass
            # Calculate cost even for failures (costs are still incurred)
            usage_data = {"duration_seconds": duration_seconds}
            cost_metrics = cost_calculator.calculate_cost(
                extractor_name=extractor_type,
                usage_data=usage_data,
                api_response=api_response
            )
            
            try:
                db.execute(
                    update(AudioExtractionJob)
                    .where(AudioExtractionJob.uuid == job_uuid)
                    .values(
                        status=ExtractionStatus.FAILURE,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        cost=cost_metrics.calculated_cost,
                    )
                )
                db.commit()
            except Exception:
                pass
            mark_task_failed(audio_uuid, job_uuid)
            retry_config = get_retry_config(extractor_type)
            raise self.retry(
                exc=e,
                countdown=retry_config["countdown"],
                max_retries=retry_config["max_retries"],
            )


@celery_app.task(bind=True)
def process_image_with_extractor(
    self, job_uuid: str, image_uuid: str, file_path: str, extractor_type: str
):
    """
    Process an image file with the specified extractor.
    """
    start_time = datetime.now(timezone.utc)
    # Initialize api_response before try block to avoid UnboundLocalError
    api_response = None
    
    with get_db_session_context() as db:
        try:
            # Update job status to Processing
            db.execute(
                update(ImageExtractionJob)
                .where(ImageExtractionJob.uuid == job_uuid)
                .values(status=ExtractionStatus.PROCESSING, start_time=start_time)
            )
            db.commit()

            # Resolve file path (S3 vs local)
            local_file_path = None
            image = db.query(Image).filter(Image.uuid == image_uuid).first()
            if not image:
                raise RuntimeError(f"Image {image_uuid} not found")
            if file_path.startswith("projects/"):
                shared_path = download_to_shared_volume(image_uuid, file_path, image.filename)
                local_file_path = shared_path
            elif os.path.exists(file_path):
                local_file_path = file_path
            else:
                raise RuntimeError(f"File not found: {file_path}")

            # Get image reader and read
            reader = get_image_reader(extractor_type)
            result = reader.read(local_file_path)
            
            # Validate result format
            if not isinstance(result, dict):
                raise RuntimeError(
                    f"Extractor {extractor_type} returned invalid result type: {type(result)}. "
                    f"Expected dict with 'content' and 'metadata' keys."
                )
            
            # Extract API response for cost calculation (already initialized above)
            if "_api_response" in result:
                api_response = result["_api_response"]

            # Extract content and metadata from result
            content_dict = result.get("content", {})
            metadata_dict = result.get("metadata", {})
            
            # Validate that content exists (even if empty - images with no text are valid)
            if content_dict is None:
                raise RuntimeError(
                    f"Extractor {extractor_type} returned None for content. "
                    f"Expected dict (can be empty for images with no text)."
                )
            
            # Ensure content_dict is a dict
            if not isinstance(content_dict, dict):
                raise RuntimeError(
                    f"Extractor {extractor_type} returned invalid content type: {type(content_dict)}. "
                    f"Expected dict."
                )
            
            # Log warning if content is empty (but don't fail - images with no text are valid)
            text_content = (
                content_dict.get("TEXT", "")
                or content_dict.get("COMBINED", "")
                or content_dict.get("MARKDOWN", "")
                or ""
            )
            if not text_content or not text_content.strip():
                logger.info(
                    f"Extractor {extractor_type} returned empty text content. "
                    f"This is normal for images with no readable text. "
                    f"Content keys: {list(content_dict.keys())}"
                )
            
            # Ensure metadata includes extractor info
            if not metadata_dict:
                metadata_dict = {}
            metadata_dict["extractor"] = extractor_type
            
            image_content = ImageContent(
                uuid=str(uuid.uuid4()),
                image_file_uuid=image_uuid,
                extraction_job_uuid=job_uuid,
                content=content_dict,
                metadata_=metadata_dict,
            )
            db.add(image_content)

            # Calculate cost using the new cost calculator (image_count is always 1 for single image)
            usage_data = {"image_count": 1}
            cost_metrics = cost_calculator.calculate_cost(
                extractor_name=extractor_type,
                usage_data=usage_data,
                api_response=api_response
            )
            
            # Track usage in Langfuse if available
            cost_calculator.track_usage(
                extractor_name=extractor_type,
                usage_data=usage_data,
                cost_metrics=cost_metrics,
                trace_id=job_uuid
            )

            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            db.execute(
                update(ImageExtractionJob)
                .where(ImageExtractionJob.uuid == job_uuid)
                .values(
                    status=ExtractionStatus.SUCCESS,
                    end_time=end_time,
                    latency_ms=latency_ms,
                    cost=cost_metrics.calculated_cost,
                )
            )
            db.commit()
            mark_task_complete(image_uuid, job_uuid)
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            try:
                db.rollback()
            except Exception:
                pass
            # Calculate cost even for failures (costs are still incurred)
            usage_data = {"image_count": 1}
            cost_metrics = cost_calculator.calculate_cost(
                extractor_name=extractor_type,
                usage_data=usage_data,
                api_response=api_response
            )
            
            try:
                db.execute(
                    update(ImageExtractionJob)
                    .where(ImageExtractionJob.uuid == job_uuid)
                    .values(
                        status=ExtractionStatus.FAILURE,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        cost=cost_metrics.calculated_cost,
                    )
                )
                db.commit()
            except Exception:
                pass
            mark_task_failed(image_uuid, job_uuid)
            logger.error(
                f"Failed to process image {image_uuid} with {extractor_type}: {str(e)}"
            )
            logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.error(
                    f"Caused by: {type(e.__cause__).__name__}: {str(e.__cause__)}"
                )
            retry_config = get_retry_config(extractor_type)
            raise self.retry(
                exc=e,
                countdown=retry_config["countdown"],
                max_retries=retry_config["max_retries"],
            )