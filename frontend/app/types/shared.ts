/**
 * Shared types used across the application
 */

// Common pagination types
export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationMeta;
}

// Sorting types
export type SortDirection = 'asc' | 'desc';

export interface SortConfig<T extends string = string> {
  field: T | null;
  direction: SortDirection;
}

// Common status types
export type JobStatus = 'NOT_STARTED' | 'Processing' | 'Completed' | 'Failed';

export type UserRole = 'admin' | 'user';

// Bounding box for images
export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

// Image item
export interface ImageItem {
  url: string;
  width?: number;
  height?: number;
  bounding_box?: BoundingBox;
  order?: number;
}

// Content view types
export type ContentViewType = 'markdown' | 'latex' | 'images' | 'raw';

// Base entity with common fields
export interface BaseEntity {
  uuid: string;
  created_at: string;
}

// User-related types
export interface UserInfo {
  id?: number;
  name?: string;
  email?: string;
}

// Ownership information
export interface Ownership {
  owner_name?: string;
  is_owner?: boolean;
}

// Feedback/Rating types
export interface Rating {
  rating: number;
  comment?: string;
}

export interface FeedbackInfo {
  uuid: string;
  user_id?: number;
  user_name?: string;
  rating: number;
  comment: string;
  created_at: string;
}

// Annotation types
export interface TextSelection {
  text: string;
  selection_start: number;
  selection_end: number;
}

export interface AnnotationBase extends BaseEntity, UserInfo, TextSelection {
  page_number: number;
  comment: string;
}

// Extraction job base
export interface ExtractionJobBase extends BaseEntity {
  extractor: string;
  status: JobStatus;
  start_time?: string;
  end_time?: string;
  latency_ms?: number;
  cost?: number;
  pages_annotated: number;
  total_rating?: number;
  total_feedback_count: number;
}

// API Error type
export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  status?: number;
  statusText?: string;
}

// Upload response types
export interface UploadFailure {
  filename: string;
  error: string;
}

export interface UploadResponse {
  message: string;
  document_uuids?: string[];
  audio_uuids?: string[];
  failed_uploads: UploadFailure[];
}

// Table column configuration
export interface TableColumn<T = any> {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (item: T) => React.ReactNode;
  width?: string;
}

// Modal states
export interface ModalState<T = null> {
  open: boolean;
  data: T;
}

// Generic project type
export interface ProjectBase extends BaseEntity, Ownership {
  name: string;
  description?: string;
}

// Generic file type
export interface FileBase extends BaseEntity, Ownership {
  filename: string;
  filepath: string;
  file_type?: string;
}

// Query parameters for lists
export interface ListQueryParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_direction?: SortDirection;
  filter?: Record<string, any>;
}
