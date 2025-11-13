/**
 * Barrel export for all types
 */

export * from './shared';

// Re-export types from services for convenience
export type {
  Project,
  ProjectCreateRequest,
  Document,
  DocumentExtractionJob,
  DocumentPageContent,
  FeedbackRequest,
  FeedbackResponse,
  AnnotationPayload,
  AnnotationResponse,
  AnnotationListItem,
  UserRatingBreakdown,
  PageAverageRating,
  ExtractorInfo,
  ExtractorCategory,
  ExtractorsResponse,
  DocumentSortFieldType,
  SortDirectionType,
} from '../services/pdfApi';

export type {
  UserProfile,
} from '../services/api';

export type {
  AudioProject,
  AudioProjectCreateRequest,
  AudioItem,
  AudioExtractionJob,
  AudioAnnotation,
  AudioSegmentFeedback,
  AudioSegmentAverageRating,
} from '../services/audioApi';

export type {
  ImageProject,
  ImageProjectCreateRequest,
  ImageItem,
  ImageExtractionJob,
  ImageContent,
  ImageFeedback,
  ImageFeedbackRequest,
  ImageAnnotation,
  ImageAnnotationCreateRequest,
  ImageAverageRating,
  PaginatedImagesResponse,
  ImageExtractorInfo,
} from '../services/imageApi';
