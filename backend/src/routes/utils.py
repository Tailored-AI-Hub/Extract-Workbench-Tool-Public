"""
Shared utility functions for routes
"""
from datetime import datetime, timezone
from typing import Optional
from io import BytesIO
import os
import tempfile
from urllib.parse import quote

try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from loguru import logger
from src.factory.audio import get_audio_reader
from src.factory.image import get_image_reader
from src.factory.pdf import get_reader, READER_MAP
from src.models import PDFExtractorType, AudioExtractorType, ImageExtractorType, ExtractorInfo


def to_utc_isoformat(dt: datetime) -> str:
    """
    Convert a datetime to ISO format string with UTC timezone.
    Handles both timezone-aware and naive datetimes.
    Naive datetimes are assumed to be UTC.
    """
    if dt is None:
        return None
    # If datetime is naive (no timezone info), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to UTC if it's in a different timezone
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def get_image_dimensions(content: bytes) -> tuple[Optional[int], Optional[int]]:
    """
    Extract image dimensions (width, height) from file content.
    Returns (width, height) tuple, or (None, None) if extraction fails.
    """
    if not HAS_PIL:
        return (None, None)
    
    try:
        image = PILImage.open(BytesIO(content))
        return (image.width, image.height)
    except Exception as e:
        logger.warning(f"Failed to extract image dimensions: {e}")
        return (None, None)


def get_extractor_display_name(extractor_type: str, extractor_category: str = "document") -> str:
    """
    Get the display name for an extractor by looking up its get_information() method.
    
    Args:
        extractor_type: The extractor ID (e.g., "gpt-5", "gpt-5-mini", "assemblyai")
        extractor_category: One of "document", "image", "audio"
    
    Returns:
        The formatted display name from the extractor's get_information() method,
        or the extractor_type if lookup fails.
    """
    try:
        if extractor_category == "image":
            # get_image_reader already returns an instance
            extractor_instance = get_image_reader(extractor_type)
        elif extractor_category == "audio":
            # get_audio_reader already returns an instance
            extractor_instance = get_audio_reader(extractor_type)
        else:  # document
            if extractor_type not in READER_MAP:
                return extractor_type
            reader_factory = READER_MAP[extractor_type]
            # Handle both class instances and callable factories (lambdas)
            extractor_instance = reader_factory() if callable(reader_factory) else reader_factory
        
        info = extractor_instance.get_information()
        return info.get("name", extractor_type)
    except Exception as e:
        logger.warning(f"Failed to get display name for extractor {extractor_type} ({extractor_category}): {e}")
        return extractor_type


def get_audio_duration(content: bytes, filename: str) -> Optional[float]:
    """
    Extract audio duration in seconds from file content.
    Returns None if extraction fails or mutagen is not available.
    """
    if not HAS_MUTAGEN:
        return None
    
    temp_path = None
    try:
        # Write content to temp file (mutagen needs a file path)
        suffix = os.path.splitext(filename)[1] or '.mp3'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content)
            temp_path = f.name
        
        # Extract duration using mutagen
        audio = MutagenFile(temp_path)
        if audio and hasattr(audio, 'info') and audio.info:
            duration = getattr(audio.info, 'length', None)
            if duration and duration > 0:
                return float(duration)
        
        return None
    except Exception as e:
        logger.debug(f"Could not extract duration from {filename}: {e}")
        return None
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def safe_content_disposition(filename: str) -> str:
    """
    Create a safe Content-Disposition header value that handles Unicode filenames.
    Uses RFC 5987 encoding for Unicode characters.
    """
    try:
        # Try to encode as ASCII for simple filenames
        filename.encode('ascii')
        # If successful, use simple format
        return f'inline; filename="{filename}"'
    except UnicodeEncodeError:
        # Filename contains non-ASCII characters, use RFC 5987 encoding
        # Format: filename="fallback"; filename*=UTF-8''encoded
        ascii_fallback = filename.encode('ascii', errors='ignore').decode('ascii')
        if not ascii_fallback:
            ascii_fallback = "file"
        utf8_filename = quote(filename, safe='')
        return f'inline; filename="{ascii_fallback}"; filename*=UTF-8\'\'{utf8_filename}'

