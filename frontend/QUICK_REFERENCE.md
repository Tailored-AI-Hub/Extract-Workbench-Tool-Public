# Frontend Architecture - Quick Reference Guide

## Directory Structure at a Glance

```
app/
├── components/
│   ├── ui/                          # shadcn/ui component library
│   ├── Layout.tsx                   # Main layout wrapper
│   ├── Sidebar.tsx                  # Navigation sidebar
│   ├── ProtectedRoute.tsx           # Auth guard component
│   ├── ErrorBoundary.tsx            # Error handling
│   ├── LoginForm.tsx                # Auth entry point
│   ├── NewProjectModal.tsx          # Project creation
│   ├── UploadFileModal.tsx          # File upload
│   └── DynamicModals.tsx            # Lazy-loaded modals
│
├── projects/                        # Document extraction feature
│   ├── components/
│   │   ├── extractors/              # Viewer & control components
│   │   ├── documents/               # Document management
│   │   ├── project-card/            # Project cards
│   │   └── new-project/             # Project setup forms
│   ├── hooks/
│   │   ├── usePageContent.ts        # Page content fetching
│   │   ├── usePDFViewer.ts          # PDF rendering
│   │   ├── useExtractionJobPolling.ts # Job status polling
│   │   └── useImageViewer.ts        # Image handling
│   ├── utils/
│   │   ├── status-helpers.ts        # Status display logic
│   │   ├── formatters.ts            # Data formatting
│   │   └── content-helpers.ts       # Content utilities
│   ├── types/
│   │   └── index.ts                 # Feature-specific types
│   └── [projectId]/                 # Dynamic routes
│
├── audio/                           # Audio extraction feature (parallel structure)
│   ├── components/                  # Audio-specific components
│   ├── hooks/                       # Audio-specific hooks
│   ├── page.tsx                     # Audio projects list
│   └── projects/[projectId]/        # Audio project routes
│
├── services/
│   ├── api.ts                       # Document API client (40+ endpoints)
│   └── audioApi.ts                  # Audio API client (20+ endpoints)
│
├── contexts/
│   └── AuthContext.tsx              # Global auth state
│
├── lib/
│   ├── api-utils.ts                 # Fetch with retry/timeout
│   └── utils.ts                     # Helper functions
│
├── constants/
│   └── index.ts                     # Config constants
│
├── types/
│   └── shared.ts                    # Shared type definitions
│
├── layout.tsx                       # Root layout
├── page.tsx                         # Document projects home
└── providers.tsx                    # Global providers setup
```

## Data Flow Patterns

### 1. Authentication Flow
```
app/page.tsx
    ↓
ProtectedRoute (checks useAuth())
    ↓
LoginForm.tsx (if no auth) → AuthContext.login/signup
    ↓
Layout.tsx (if authenticated)
    ↓
Feature Pages
```

### 2. Project Listing Flow
```
app/page.tsx (Container)
    ↓
useQuery(['projects'], apiService.getProjects)
    ↓
React Query (caching)
    ↓
ProjectCard.tsx (Presentation)
    ↓
useMutation (create/delete)
```

### 3. Document Extraction Flow
```
app/projects/[projectId]/documents/[documentId]/extractors/page.tsx
    ├─ usePageContent (fetch extraction job content)
    ├─ useExtractionJobPolling (3s polling)
    └─ Complex UI State
        ├─ ExtractorSelector (job picker)
        ├─ ContentViewSelector (view mode)
        ├─ Dynamic Viewer (PDF/Markdown/LaTeX/Images)
        ├─ AnnotationPanel (user annotations)
        └─ RatingControl (feedback)
```

## Key Hooks & Patterns

### Polling Hooks
```typescript
// Document extraction
useExtractionJobPolling(projectId, documentId, token, jobs, setJobs)
  → Returns: { retryingJobs, retryExtractionJob, fetchExtractionJobs }

// Audio extraction
useAudioExtractionJobPolling(projectId, audioId, token, jobs, setJobs)
  → Returns: { fetchExtractionJobs }
  → Features: Fast (3s) during processing, Slow (10s) for ratings
```

### Content Fetching
```typescript
usePageContent(projectId, documentId, token, extractionJobs)
  → Fetches page content + annotations
  → Filters by extractor and page number
```

### PDF Rendering
```typescript
usePDFViewer(pdfUrl, token, activeTab, currentPage, setCurrentPage)
  → Dynamic PDF.js loading from CDN
  → Client-side rendering only (SSR disabled)
```

## State Management Layers

### Level 1: Authentication (Global)
- Source: AuthContext
- Persistence: localStorage ('auth_token')
- Methods: login, signup, logout, retryAuth

### Level 2: Server State (Cached)
- Source: React Query
- Query Keys: PROJECTS, DOCUMENTS, EXTRACTION_JOBS, etc.
- Cache: Automatic invalidation on mutations

### Level 3: UI State (Component)
- Source: useState
- Examples: Modal open/close, selected extractor, view mode
- Scope: Single component or feature

### Level 4: Transient Data
- Source: localStorage
- Examples: sidebar-collapsed, theme
- Sync: Manual in components

## API Integration Pattern

### Service Classes (Singleton)
```typescript
apiService {
  // Auth
  login, signup, getUserProfile, changePassword
  
  // Projects & Documents
  getProjects, createProject, deleteProject
  getProjectDocuments, getDocument, deleteDocument
  
  // Extraction
  getDocumentExtractionJobs, retryExtractionJob
  getExtractionJobPages
  
  // Annotations & Feedback
  createAnnotation, getAnnotations, deleteAnnotation
  submitFeedback, getPageFeedback, getRatingBreakdown
  
  // Admin
  adminListUsers, adminApproveUser, adminActivateUser, ...
}

audioApi {
  // Same structure for audio extraction
  getProjects, createProject, deleteProject
  getProjectAudios, uploadAudios, deleteAudio
  getAudioExtractionJobs, getExtractionJobSegments
  // ... annotations, feedback, ratings
}
```

### Fetch Enhancement Stack
```
enhancedFetch()
  ├─ requestCache.get() // Deduplication (GET only, 1s TTL)
  └─ fetchWithRetry()
     ├─ Exponential backoff
     ├─ Retryable statuses: [408, 429, 500, 502, 503, 504]
     └─ fetchWithTimeout() // 30s default
```

## Component Organization

### Presentation (Dumb)
- ProjectCard, DocumentsTable, ExtractionJobsTable
- No API calls, no side effects
- Props-driven rendering

### Container (Smart)
- app/page.tsx, /audio/page.tsx
- Manage React Query
- Handle mutations
- Manage modals & forms

### Complex/Stateful
- AnnotationPanel (text selection + annotations)
- ContentViewSelector (dynamic component loading)
- PDFViewer (PDF.js integration)
- LatexRenderer (math equation rendering)

## Performance Optimizations

### Code Splitting
```typescript
DynamicLatexRenderer      // KaTeX - lazy load (ssr: false)
DynamicMarkdownRenderer   // react-markdown - lazy load
DynamicPDFViewer          // pdf.js - lazy load (ssr: false)
DynamicImagesRenderer     // image display - lazy load
DynamicUploadFileModal    // modal - lazy load
DynamicNewProjectModal    // modal - lazy load
```

### Request Optimization
- Retry with exponential backoff (3 attempts)
- Request deduplication (1 second window)
- Timeout handling (30 second default)
- Conditional queries (enabled: !!token)

### Component Optimization
- useCallback in polling hooks
- useMemo in admin page
- Image lazy loading attribute
- PDF.js CDN (not bundled)

## Error Handling Strategy

### Boundaries
- ErrorBoundary wraps main content
- Catches React rendering errors
- Shows stack traces in development
- Allows retry or refresh

### API Errors
- createApiError() extracts detail/message
- Retry logic for transient errors
- Token cleanup on 401/auth errors
- Timeout errors (408) trigger retry

### Component Errors
- Try/catch in async handlers
- User-facing error messages
- Loading/error states in queries
- Silent failures logged to console

## Type Safety

### Type Distribution
- **51 type definitions** across services
- **Strict mode** enabled in tsconfig
- **Path aliases**: @/* → app/*
- **Union types** for statuses (NOT_STARTED | Processing | Completed | Failed)

### API Types Pattern
```typescript
Request   → ProjectCreateRequest
Response  → Project
Pagination → PaginationMeta, PaginatedDocumentsResponse
Status    → JobStatus, ContentViewType
```

### Component Props Pattern
```typescript
interface ComponentProps {
  // Data
  data: T[];
  
  // Callbacks
  onSelect: (item: T) => void;
  onChange: (value: string) => void;
  
  // State
  loading: boolean;
  error: string | null;
  
  // Options
  disabled?: boolean;
  variant?: 'default' | 'secondary';
}
```

## Routing Map

```
GET /                                    → Home (Documents)
  GET /projects/[projectId]              → Project Detail
  POST /projects (via NewProjectModal)   → Create
  DELETE /projects/[projectId]           → Delete
  GET /projects/[projectId]/documents/[documentId]/extractors
                                         → Extractor UI

GET /audio                               → Audio Projects
  GET /audio/projects/[projectId]        → Audio Project Detail
  GET /audio/projects/[projectId]/audios/[audioId]/extractors
                                         → Audio Extractor UI

GET /admin                               → Admin Dashboard
  POST /admin/* (admin mutations)        → User management

Routes are client-side protected (ProtectedRoute)
No server-side middleware protection
```

## Configuration Constants

### Timeouts & Polling
```
API_TIMEOUT: 30,000 ms (30s)
EXTRACTION_JOB_POLL: 3,000 ms (3s)
AUDIO_JOB_POLL: 3,000 ms (3s)
AUDIO_RATING_POLL: 10,000 ms (10s)
```

### File Upload
```
MAX_FILE_SIZE: 50 MB
MAX_FILES_PER_UPLOAD: 10
ALLOWED_DOCUMENT_TYPES: pdf, png, jpeg, jpg, webp
ALLOWED_AUDIO_TYPES: mp3, wav, ogg, flac
```

### Feature Flags
```
ENABLE_AUDIO_EXTRACTION: true
ENABLE_LATEX_RENDERING: true
ENABLE_IMAGE_EXTRACTION: true
ENABLE_ANNOTATIONS: true
ENABLE_RATINGS: true
```

## Key Files Reference

| File | Purpose | Key Exports |
|------|---------|-------------|
| AuthContext.tsx | Auth state management | useAuth(), AuthProvider |
| api.ts | Document API | apiService (singleton) |
| audioApi.ts | Audio API | audioApi (singleton) |
| api-utils.ts | Network utilities | enhancedFetch(), RequestCache |
| DynamicComponents.tsx | Code splitting | DynamicLatexRenderer, etc. |
| useExtractionJobPolling.ts | Job polling | useExtractionJobPolling() |
| ErrorBoundary.tsx | Error handling | ErrorBoundary, withErrorBoundary |
| constants/index.ts | Configuration | API_CONFIG, ROUTES, etc. |
