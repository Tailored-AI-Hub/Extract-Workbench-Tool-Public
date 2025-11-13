import { DocumentExtractionJob, DocumentPageContent, AnnotationResponse, Document } from "../../services/pdfApi";

export type ContentViewMode = 'combined' | 'text' | 'table' | 'markdown' | 'latex' | 'images';

export type SortDirection = 'asc' | 'desc';

export type SortField = keyof DocumentExtractionJob | null;

export type DocumentSortField = keyof Document | null;

// Specific types for document sorting
export type DocumentSortFieldType = 'uploaded_at' | 'filename' | 'file_type' | 'page_count' | 'owner_name' | 'uuid';
export type SortDirectionType = 'asc' | 'desc';

export interface PDFViewerProps {
  pdfUrl: string;
  token: string | null;
  currentPage: number;
  activeTab: string;
}

export interface PageNavigationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export interface RatingControlProps {
  rating: number;
  onRatingChange: (rating: number) => void;
  submitting: boolean;
  error?: string | null;
}

export interface ExtractorSelectorProps {
  selectedExtractor: string;
  extractionJobs: DocumentExtractionJob[];
  onSelectExtractor: (extractor: string) => void;
}

export interface ContentViewSelectorProps {
  viewMode: ContentViewMode;
  onViewModeChange: (mode: ContentViewMode) => void;
  hasCombined: boolean;
  hasText: boolean;
  hasTable: boolean;
  hasMarkdown: boolean;
  hasLatex: boolean;
  hasImages: boolean;
}

export interface AnnotationPanelProps {
  content: any;
  viewMode: ContentViewMode;
  loading: boolean;
  error: string | null;
  annotations: AnnotationResponse[];
  selectedExtractor: string;
  extractionJobs: DocumentExtractionJob[];
  currentPage: number;
  documentUuid: string;
  token: string | null;
  onAnnotationsChange: (annotations: AnnotationResponse[]) => void;
}

export interface ExtractionJobsTableProps {
  jobs: DocumentExtractionJob[];
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: keyof DocumentExtractionJob) => void;
  onViewExtractor: (extractor: string) => void;
  onRetryJob: (jobUuid: string) => void;
  retryingJobs: Set<string>;
}

export interface DocumentsTableProps {
  projectId: string;
  documents: Document[];
  isOwner: boolean;
  onDelete: (document: Document) => void;
  deleting: boolean;
  sortField: DocumentSortField;
  sortDirection: SortDirection;
  onSort: (field: keyof Document) => void;
}

