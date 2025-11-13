/**
 * Application-wide constants
 */

// API Configuration
export const API_CONFIG = {
  TIMEOUT: 30000, // 30 seconds
  MAX_RETRIES: 2,
  RETRY_DELAY: 1000, // 1 second
} as const;

// Polling Configuration
export const POLLING_CONFIG = {
  EXTRACTION_JOB_INTERVAL: 3000, // 3 seconds
  AUDIO_EXTRACTION_JOB_INTERVAL: 3000, // 3 seconds
} as const;

// Pagination Configuration
export const PAGINATION_CONFIG = {
  DEFAULT_PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [5, 10, 20, 50, 100],
  DEFAULT_PAGE: 1,
} as const;

// File Upload Configuration
export const FILE_UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50 MB
  MAX_FILES_PER_UPLOAD: 10,
  ALLOWED_DOCUMENT_TYPES: [
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/webp',
  ],
  ALLOWED_AUDIO_TYPES: [
    'audio/mpeg',
    'audio/mp3',
    'audio/wav',
    'audio/ogg',
    'audio/flac',
  ],
} as const;

// UI Configuration
export const UI_CONFIG = {
  TOAST_DURATION: 3000, // 3 seconds
  DEBOUNCE_DELAY: 300, // 300ms
  IMAGE_MAX_HEIGHT: 600, // pixels
  PDF_SCALE_FACTOR: 1.5,
} as const;

// Storage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'token',
  SIDEBAR_COLLAPSED: 'sidebarCollapsed',
  THEME: 'theme',
} as const;

// Query Keys for React Query
export const QUERY_KEYS = {
  PROJECTS: 'projects',
  PROJECT: 'project',
  DOCUMENTS: 'documents',
  DOCUMENT: 'document',
  EXTRACTION_JOBS: 'extraction-jobs',
  ANNOTATIONS: 'annotations',
  USER_PROFILE: 'user-profile',
  EXTRACTORS: 'extractors',
  AUDIO_PROJECTS: 'audio-projects',
  AUDIO_PROJECT: 'audio-project',
  AUDIO_FILES: 'audio-files',
  AUDIO_FILE: 'audio-file',
  AUDIO_EXTRACTION_JOBS: 'audio-extraction-jobs',
  AUDIO_ANNOTATIONS: 'audio-annotations',
  ADMIN_USERS: 'admin-users',
} as const;

// Job Statuses
export const JOB_STATUS = {
  NOT_STARTED: 'NOT_STARTED',
  PROCESSING: 'Processing',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
} as const;

// User Roles
export const USER_ROLES = {
  ADMIN: 'admin',
  USER: 'user',
} as const;

// Content View Types
export const CONTENT_VIEW_TYPES = {
  MARKDOWN: 'markdown',
  LATEX: 'latex',
  IMAGES: 'images',
  RAW: 'raw',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  SESSION_EXPIRED: 'Your session has expired. Please log in again.',
  FILE_TOO_LARGE: 'File size exceeds the maximum allowed size.',
  INVALID_FILE_TYPE: 'Invalid file type. Please select a supported file.',
  GENERIC_ERROR: 'An error occurred. Please try again.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  PROJECT_CREATED: 'Project created successfully.',
  PROJECT_DELETED: 'Project deleted successfully.',
  DOCUMENT_UPLOADED: 'Document uploaded successfully.',
  DOCUMENT_DELETED: 'Document deleted successfully.',
  ANNOTATION_CREATED: 'Annotation created successfully.',
  ANNOTATION_DELETED: 'Annotation deleted successfully.',
  RATING_SUBMITTED: 'Rating submitted successfully.',
  PASSWORD_CHANGED: 'Password changed successfully.',
} as const;

// Routes
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  PROJECTS: '/',
  PROJECT_DETAIL: (projectId: string) => `/projects/${projectId}`,
  DOCUMENT_EXTRACTOR: (projectId: string, documentId: string) =>
    `/projects/${projectId}/documents/${documentId}/extractors`,
  AUDIO_PROJECTS: '/audio',
  AUDIO_PROJECT_DETAIL: (projectId: string) => `/audio/projects/${projectId}`,
  AUDIO_EXTRACTOR: (projectId: string, audioId: string) =>
    `/audio/projects/${projectId}/audios/${audioId}/extractors`,
  ADMIN: '/admin',
} as const;

// Feature Flags (for gradual rollout or A/B testing)
export const FEATURE_FLAGS = {
  ENABLE_AUDIO_EXTRACTION: true,
  ENABLE_LATEX_RENDERING: true,
  ENABLE_IMAGE_EXTRACTION: true,
  ENABLE_ANNOTATIONS: true,
  ENABLE_RATINGS: true,
} as const;
