from pydantic import BaseModel
from typing import Optional, List
from .enums import ExtractionStatus

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Document Schemas
class DocumentResponse(BaseModel):
    uuid: str
    filename: str
    filepath: str
    uploaded_at: str
    page_count: Optional[int]
    file_type: str
    owner_name: Optional[str] = None

class UploadResponse(BaseModel):
    message: str
    document_uuid: str

class MultipleUploadResponse(BaseModel):
    message: str
    document_uuids: List[str]
    failed_uploads: List[dict] = []

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool

class PaginatedDocumentsResponse(BaseModel):
    documents: List[DocumentResponse]
    pagination: PaginationMeta

# Project Schemas
class ProjectResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None
    created_at: str
    owner_name: Optional[str] = None
    is_owner: Optional[bool] = None

class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

# Extraction Schemas
class DocumentExtractionJobResponse(BaseModel):
    uuid: str
    document_uuid: str
    extractor: str
    extractor_display_name: str  # Human-readable extractor name
    status: ExtractionStatus
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    latency_ms: Optional[int] = None
    cost: Optional[float] = None
    pages_annotated: int = 0  # Number of pages with feedback
    total_rating: Optional[float] = None  # Average rating across all pages
    total_feedback_count: int = 0  # Total number of feedback entries

class DocumentPageFeedbackResponse(BaseModel):
    uuid: str
    document_uuid: str
    page_number: int
    extraction_job_uuid: str
    feedback_type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

class DocumentPageContentResponse(BaseModel):
    uuid: str
    extraction_job_uuid: str
    page_number: int
    content: dict
    feedback: Optional[DocumentPageFeedbackResponse] = None

class DocumentPageFeedbackRequest(BaseModel):
    document_uuid: str
    page_number: int
    extraction_job_uuid: str
    rating: Optional[int] = None  # 1-5 rating
    comment: Optional[str] = None

# Extractor Schemas
class ExtractorInfo(BaseModel):
    id: str
    name: str
    description: str
    cost_per_page: float
    support_tags: List[str] = []

class ExtractorCategory(BaseModel):
    category: str
    extractors: List[ExtractorInfo]

class ExtractorsResponse(BaseModel):
    pdf_extractors: List[ExtractorCategory]
    image_extractors: List[ExtractorCategory]

class UploadWithExtractorsRequest(BaseModel):
    selected_extractors: List[str]

# Annotation Schemas
class AnnotationCreateRequest(BaseModel):
    # Match frontend payload keys
    documentId: str
    extractionJobUuid: str
    pageNumber: int
    text: str
    comment: str | None = None
    selectionStart: int
    selectionEnd: int

class AnnotationResponse(BaseModel):
    uuid: str
    document_uuid: str
    extraction_job_uuid: str
    page_number: int
    text: str
    comment: str
    selection_start: int
    selection_end: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

class UserRatingBreakdown(BaseModel):
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    average_rating: float
    pages_rated: int
    total_ratings: int
    latest_comment: Optional[str] = None
    latest_rated_at: str

class AnnotationListItem(BaseModel):
    uuid: str
    page_number: int
    extractor: str
    extraction_job_uuid: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    text: str
    comment: str
    selection_start: int
    selection_end: int
    created_at: str

# -------------------- Audio Schemas --------------------
class AudioProjectResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None
    created_at: str
    owner_name: Optional[str] = None
    is_owner: Optional[bool] = None

class AudioProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class AudioResponse(BaseModel):
    uuid: str
    filename: str
    filepath: str
    uploaded_at: str
    duration_seconds: Optional[float] = None
    owner_name: Optional[str] = None

class PaginatedAudiosResponse(BaseModel):
    audios: List[AudioResponse]
    pagination: PaginationMeta

class AudioExtractionJobResponse(BaseModel):
    uuid: str
    audio_uuid: str
    extractor: str
    extractor_display_name: str  # Human-readable extractor name
    status: ExtractionStatus
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    latency_ms: Optional[int] = None
    cost: Optional[float] = None
    segments_annotated: int = 0
    total_rating: Optional[float] = None
    total_feedback_count: int = 0

class AudioSegmentFeedbackResponse(BaseModel):
    uuid: str
    audio_uuid: str
    segment_number: int
    extraction_job_uuid: str
    feedback_type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

class AudioSegmentContentResponse(BaseModel):
    uuid: str
    extraction_job_uuid: str
    segment_number: int
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    content: dict
    feedback: Optional[AudioSegmentFeedbackResponse] = None

class AudioSegmentFeedbackRequest(BaseModel):
    audio_uuid: str
    segment_number: int
    extraction_job_uuid: str
    rating: Optional[int] = None
    comment: Optional[str] = None

class AudioAnnotationCreateRequest(BaseModel):
    audioId: str
    extractionJobUuid: str
    segmentNumber: int
    text: str
    comment: Optional[str] = None
    selectionStartChar: Optional[int] = None
    selectionEndChar: Optional[int] = None

class AudioAnnotationListItem(BaseModel):
    uuid: str
    segment_number: int
    extractor: str
    extraction_job_uuid: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    text: str
    comment: Optional[str] = None
    created_at: str

class AudioAnnotationResponse(BaseModel):
    uuid: str
    audio_uuid: str
    extraction_job_uuid: str
    segment_number: int
    text: str
    comment: Optional[str] = None
    selection_start_char: Optional[int] = None
    selection_end_char: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

# -------------------- Image Schemas --------------------
class ImageProjectResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None
    created_at: str
    owner_name: Optional[str] = None
    is_owner: Optional[bool] = None

class ImageProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class ImageResponse(BaseModel):
    uuid: str
    filename: str
    filepath: str
    uploaded_at: str
    width: Optional[int] = None
    height: Optional[int] = None
    owner_name: Optional[str] = None

class PaginatedImagesResponse(BaseModel):
    images: List[ImageResponse]
    pagination: PaginationMeta

class ImageExtractionJobResponse(BaseModel):
    uuid: str
    image_uuid: str
    extractor: str
    extractor_display_name: str  # Human-readable extractor name
    status: ExtractionStatus
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    latency_ms: Optional[int] = None
    cost: Optional[float] = None
    annotated: int = 0  # Number of annotations
    total_rating: Optional[float] = None
    total_feedback_count: int = 0

class ImageContentResponse(BaseModel):
    uuid: str
    extraction_job_uuid: str
    content: dict
    metadata_: Optional[dict] = None
    feedback: Optional["ImageFeedbackResponse"] = None

class ImageFeedbackRequest(BaseModel):
    image_uuid: str
    extraction_job_uuid: str
    rating: Optional[int] = None  # 1-5 rating
    comment: Optional[str] = None

class ImageFeedbackResponse(BaseModel):
    uuid: str
    image_uuid: str
    extraction_job_uuid: str
    feedback_type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

class ImageAnnotationCreateRequest(BaseModel):
    imageId: str
    extractionJobUuid: str
    text: str
    comment: Optional[str] = None
    selectionStartChar: Optional[int] = None
    selectionEndChar: Optional[int] = None

class ImageAnnotationListItem(BaseModel):
    uuid: str
    image_uuid: str
    extractor: str
    extraction_job_uuid: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    text: str
    comment: Optional[str] = None
    created_at: str
    selection_start_char: Optional[int] = None
    selection_end_char: Optional[int] = None

class ImageAnnotationResponse(BaseModel):
    uuid: str
    image_uuid: str
    extraction_job_uuid: str
    text: str
    comment: Optional[str] = None
    selection_start_char: Optional[int] = None
    selection_end_char: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str