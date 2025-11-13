# Enums
from .enums import (
    ExtractionStatus,
    PDFExtractorType,
    ImageExtractorType,
    FeedbackType,
    AudioExtractorType,
)

# Database Models - Using aliases for backward compatibility
from .database import (
    User,
    PDFProject,
    PDFFile,
    PDFFileExtractionJob,
    PDFFilePageContent,
    PDFFilePageFeedback,
    PDFFileAnnotation,
    AudioProject,
    AudioFile,
    AudioFileExtractionJob,
    AudioFileContent,
    AudioFileFeedback,
    AudioFileAnnotation,
    ImageProject,
    ImageFile,
    ImageFileExtractionJob,
    ImageContent,
    ImageFeedback,
    ImageAnnotation,
)

# Create aliases for backward compatibility
Project = PDFProject
Document = PDFFile
DocumentExtractionJob = PDFFileExtractionJob
DocumentPageContent = PDFFilePageContent
DocumentPageFeedback = PDFFilePageFeedback
Annotation = PDFFileAnnotation
Audio = AudioFile
AudioExtractionJob = AudioFileExtractionJob
AudioSegmentContent = AudioFileContent
AudioSegmentFeedback = AudioFileFeedback
AudioAnnotation = AudioFileAnnotation
Image = ImageFile
ImageExtractionJob = ImageFileExtractionJob

# Schemas
from .schemas import (
    # Auth schemas
    Token,
    UserCreate,
    UserLogin,
    PasswordChange,
    # Document schemas
    DocumentResponse,
    UploadResponse,
    MultipleUploadResponse,
    PaginatedDocumentsResponse,
    PaginationMeta,
    # Project schemas
    ProjectResponse,
    ProjectCreateRequest,
    # Extraction schemas
    DocumentExtractionJobResponse,
    DocumentPageContentResponse,
    DocumentPageFeedbackRequest,
    DocumentPageFeedbackResponse,
    ExtractorInfo,
    ExtractorCategory,
    ExtractorsResponse,
    UploadWithExtractorsRequest,
    # Annotation schemas
    AnnotationCreateRequest,
    AnnotationResponse,
    UserRatingBreakdown,
    AnnotationListItem,
    # Audio schemas
    AudioProjectResponse,
    AudioProjectCreateRequest,
    AudioResponse,
    PaginatedAudiosResponse,
    AudioExtractionJobResponse,
    AudioSegmentContentResponse,
    AudioSegmentFeedbackRequest,
    AudioSegmentFeedbackResponse,
    AudioAnnotationCreateRequest,
    AudioAnnotationListItem,
    AudioAnnotationResponse,
    # Image schemas
    ImageProjectResponse,
    ImageProjectCreateRequest,
    ImageResponse,
    PaginatedImagesResponse,
    ImageExtractionJobResponse,
    ImageContentResponse,
    ImageFeedbackRequest,
    ImageFeedbackResponse,
    ImageAnnotationCreateRequest,
    ImageAnnotationListItem,
    ImageAnnotationResponse,
)

__all__ = [
    # Enums
    "ExtractionStatus",
    "PDFExtractorType", 
    "ImageExtractorType",
    "FeedbackType",
    "AudioExtractorType",
    # Database Models
    "User",
    "Project",
    "Document",
    "DocumentExtractionJob",
    "DocumentPageContent",
    "DocumentPageFeedback",
    "Annotation",
    "AudioProject",
    "Audio",
    "AudioExtractionJob",
    "AudioSegmentContent",
    "AudioSegmentFeedback",
    "AudioAnnotation",
    "ImageProject",
    "Image",
    "ImageExtractionJob",
    "ImageContent",
    "ImageFeedback",
    "ImageAnnotation",
    # Auth schemas
    "Token",
    "UserCreate",
    "UserLogin",
    "PasswordChange",
    # Document schemas
    "DocumentResponse",
    "UploadResponse",
    "MultipleUploadResponse",
    "PaginatedDocumentsResponse",
    "PaginationMeta",
    # Project schemas
    "ProjectResponse",
    "ProjectCreateRequest",
    # Extraction schemas
    "DocumentExtractionJobResponse",
    "DocumentPageContentResponse",
    "DocumentPageFeedbackRequest",
    "DocumentPageFeedbackResponse",
    "ExtractorInfo",
    "ExtractorCategory",
    "ExtractorsResponse",
    "UploadWithExtractorsRequest",
    # Annotation schemas
    "AnnotationCreateRequest",
    "AnnotationResponse",
    "UserRatingBreakdown",
    "AnnotationListItem",
    # Audio schemas
    "AudioProjectResponse",
    "AudioProjectCreateRequest",
    "AudioResponse",
    "PaginatedAudiosResponse",
    "AudioExtractionJobResponse",
    "AudioSegmentContentResponse",
    "AudioSegmentFeedbackRequest",
    "AudioSegmentFeedbackResponse",
    "AudioAnnotationCreateRequest",
    "AudioAnnotationListItem",
    "AudioAnnotationResponse",
    # Image schemas
    "ImageProjectResponse",
    "ImageProjectCreateRequest",
    "ImageResponse",
    "PaginatedImagesResponse",
    "ImageExtractionJobResponse",
    "ImageContentResponse",
    "ImageFeedbackRequest",
    "ImageFeedbackResponse",
    "ImageAnnotationCreateRequest",
    "ImageAnnotationListItem",
    "ImageAnnotationResponse",
]
