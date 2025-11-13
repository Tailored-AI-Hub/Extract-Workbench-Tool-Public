import os
import redis
import boto3
from loguru import logger
from typing import List
from .constants import (
    REDIS_BACKEND_URL, 
    AWS_BUCKET_NAME, 
    AWS_REGION, 
    SHARED_VOLUME_PATH,
    FILE_CLEANUP_TTL_SECONDS,
    CLEANUP_ON_TASK_FAILURE
)
 
# Redis client for coordination
redis_client = redis.Redis.from_url(REDIS_BACKEND_URL)

def register_extraction_tasks(document_uuid: str, job_uuids: List[str], ttl: int = None) -> None:
    """
    Register all extraction tasks for a document in Redis.
    
    Args:
        document_uuid: Document identifier
        job_uuids: List of task UUIDs for this document
        ttl: Time-to-live for Redis keys (uses default if None)
    """
    if ttl is None:
        ttl = FILE_CLEANUP_TTL_SECONDS
    
    # Store pending tasks as a set
    tasks_key = f"doc_tasks:{document_uuid}"
    redis_client.sadd(tasks_key, *job_uuids)
    redis_client.expire(tasks_key, ttl)
    
    logger.info(f"Registered {len(job_uuids)} tasks for document {document_uuid} with TTL {ttl}s")

def download_to_shared_volume(document_uuid: str, s3_key: str, filename: str) -> str:
    """
    Download S3 file to shared volume with file locking to prevent duplicate downloads.
    
    Args:
        document_uuid: Document identifier
        s3_key: S3 object key
        filename: Original filename
        
    Returns:
        Path to downloaded file in shared volume
    """
    shared_path = get_shared_file_path(document_uuid, filename)
    lock_key = f"doc_file_lock:{document_uuid}"
    
    # Use Redis lock to ensure only one task downloads the file
    with redis_client.lock(lock_key, timeout=30, blocking_timeout=60):
        # Check if file already exists
        if os.path.exists(shared_path):
            logger.info(f"File already exists in shared volume: {shared_path}")
            return shared_path
        
        # Ensure shared volume directory exists
        os.makedirs(os.path.dirname(shared_path), exist_ok=True)
        
        # Download from S3
        try:
            s3_client = boto3.client('s3', region_name=AWS_REGION)
            s3_client.download_file(AWS_BUCKET_NAME, s3_key, shared_path)
            
            # Store file path in Redis for cleanup tracking
            file_path_key = f"doc_file_path:{document_uuid}"
            redis_client.set(file_path_key, shared_path, ex=FILE_CLEANUP_TTL_SECONDS)
            
            logger.info(f"Downloaded file from S3 to shared volume: {shared_path}")
            return shared_path
            
        except Exception as e:
            logger.error(f"Failed to download file from S3: {e}")
            # Clean up any partial file
            if os.path.exists(shared_path):
                os.unlink(shared_path)
            raise

def get_shared_file_path(document_uuid: str, filename: str) -> str:
    """
    Get standardized shared volume path for a document.
    
    Args:
        document_uuid: Document identifier
        filename: Original filename
        
    Returns:
        Full path in shared volume
    """
    return os.path.join(SHARED_VOLUME_PATH, f"{document_uuid}_{filename}")

def mark_task_complete(document_uuid: str, job_uuid: str) -> None:
    """
    Mark a task as complete and check if file cleanup is needed.
    
    Args:
        document_uuid: Document identifier
        job_uuid: Task identifier
    """
    tasks_key = f"doc_tasks:{document_uuid}"
    
    # Remove task from pending set
    redis_client.srem(tasks_key, job_uuid)
    
    # Check if all tasks are complete
    if should_cleanup_file(document_uuid):
        cleanup_shared_file(document_uuid)
    
    logger.info(f"Marked task {job_uuid} as complete for document {document_uuid}")

def mark_task_failed(document_uuid: str, job_uuid: str) -> None:
    """
    Handle task failure based on STAGE configuration.
    
    Args:
        document_uuid: Document identifier
        job_uuid: Task identifier
    """
    tasks_key = f"doc_tasks:{document_uuid}"
    
    if CLEANUP_ON_TASK_FAILURE:
        # Development mode: treat failure same as completion for cleanup
        redis_client.srem(tasks_key, job_uuid)
        if should_cleanup_file(document_uuid):
            cleanup_shared_file(document_uuid)
        logger.info(f"Marked failed task {job_uuid} for cleanup (dev mode)")
    else:
        # Production mode: keep file for retry, just remove from pending
        redis_client.srem(tasks_key, job_uuid)
        logger.info(f"Marked task {job_uuid} as failed, keeping file for retry (prod mode)")

def cleanup_shared_file(document_uuid: str) -> None:
    """
    Delete file from shared volume and clean up Redis keys.
    
    Args:
        document_uuid: Document identifier
    """
    try:
        # Get file path from Redis
        file_path_key = f"doc_file_path:{document_uuid}"
        shared_path = redis_client.get(file_path_key)
        
        if shared_path:
            shared_path = shared_path.decode('utf-8')
            if os.path.exists(shared_path):
                os.unlink(shared_path)
                logger.info(f"Cleaned up shared file: {shared_path}")
        
        # Clean up Redis keys
        redis_client.delete(file_path_key)
        redis_client.delete(f"doc_tasks:{document_uuid}")
        redis_client.delete(f"doc_file_lock:{document_uuid}")
        
        logger.info(f"Cleaned up Redis keys for document {document_uuid}")
        
    except Exception as e:
        logger.warning(f"Failed to cleanup shared file for document {document_uuid}: {e}")

def should_cleanup_file(document_uuid: str) -> bool:
    """
    Check if all tasks are complete/failed and file should be cleaned up.
    
    Args:
        document_uuid: Document identifier
        
    Returns:
        True if file should be cleaned up
    """
    tasks_key = f"doc_tasks:{document_uuid}"
    remaining_tasks = redis_client.scard(tasks_key)
    
    return remaining_tasks == 0

def get_pending_tasks_count(document_uuid: str) -> int:
    """
    Get count of pending tasks for a document.
    
    Args:
        document_uuid: Document identifier
        
    Returns:
        Number of pending tasks
    """
    tasks_key = f"doc_tasks:{document_uuid}"
    return redis_client.scard(tasks_key)

def cleanup_orphaned_files() -> dict:
    """
    Cleanup files in shared volume that exceeded TTL.
    This should be called periodically by a background task.
    
    Returns:
        Statistics about cleanup operation
    """
    stats = {
        "files_cleaned": 0,
        "bytes_freed": 0,
        "errors": 0
    }
    
    try:
        # Scan for document keys that might be expired
        pattern = "doc_tasks:*"
        for key in redis_client.scan_iter(match=pattern):
            # Check if key exists and has no TTL (expired)
            ttl = redis_client.ttl(key)
            if ttl == -1:  # Key exists but has no expiration
                continue
            elif ttl == -2:  # Key doesn't exist (expired)
                # Extract document UUID from key
                document_uuid = key.decode('utf-8').replace('doc_tasks:', '')
                
                # Clean up associated file
                file_path_key = f"doc_file_path:{document_uuid}"
                shared_path = redis_client.get(file_path_key)
                
                if shared_path:
                    shared_path = shared_path.decode('utf-8')
                    if os.path.exists(shared_path):
                        file_size = os.path.getsize(shared_path)
                        os.unlink(shared_path)
                        stats["files_cleaned"] += 1
                        stats["bytes_freed"] += file_size
                        logger.info(f"Cleaned up orphaned file: {shared_path}")
                
                # Clean up Redis keys
                redis_client.delete(file_path_key)
                redis_client.delete(f"doc_file_lock:{document_uuid}")
                
    except Exception as e:
        logger.error(f"Error during orphaned file cleanup: {e}")
        stats["errors"] += 1
    
    return stats
