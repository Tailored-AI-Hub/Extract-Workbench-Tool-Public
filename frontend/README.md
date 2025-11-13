# PDF Extraction Tool - Frontend

A modern, secure document extraction platform built with Next.js 14, featuring AI-powered PDF/audio processing, user management, and real-time extraction monitoring. Recently optimized for better performance, reliability, and maintainability.

## 🚀 Features

### Core Functionality
- **Document Processing**: Upload and process PDFs with multiple AI extraction engines
- **Audio Processing**: Extract and process audio files with specialized engines
- **Project Management**: Organize documents into projects with detailed tracking
- **Real-time Monitoring**: Track extraction jobs, performance metrics, and processing status
- **Multi-Engine Support**: Choose from various extraction engines:
  - **PDF**: PyPDF2, PyMuPDF, PDFPlumber, Camelot, Tesseract, Textract, Mathpix, Tabula, Unstructured, OpenAI GPT models, MarkItDown, LlamaParse, Azure Document Intelligence
  - **Audio**: Whisper OpenAI, AssemblyAI, AWS Transcribe
  - **Image**: Tesseract, Textract, Mathpix, OpenAI GPT-4o, Azure Document Intelligence

### User Management & Security
- **Admin Approval Workflow**: New users require admin approval before accessing the platform
- **Role-Based Access Control**: Admin and user roles with appropriate permissions
- **JWT Authentication**: Secure token-based authentication with role validation
- **User Management**: Admin panel for approving, activating, and managing users

### User Experience
- **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- **Responsive Design**: Optimized for desktop and mobile devices
- **Interactive Document Viewer**: Side-by-side PDF viewing with extracted content
- **Annotation System**: Add comments and feedback to extracted content
- **Rating System**: Rate extraction quality for continuous improvement

## 🛠 Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Icons**: Lucide React
- **State Management**: TanStack Query (React Query) with caching and retry logic
- **Authentication**: JWT with role-based access control
- **Theme**: next-themes for dark/light mode support
- **Error Handling**: React Error Boundaries
- **Performance**: Dynamic imports for code splitting

## 📁 Project Structure

```
frontend/
├── app/                          # Next.js App Router
│   ├── admin/                    # Admin management pages
│   │   └── page.tsx             # User management interface
│   ├── audio/                    # Audio extraction feature
│   │   ├── components/          # Audio-specific components
│   │   │   ├── AudioAnnotationPanel.tsx
│   │   │   ├── AudioAnnotationsListTable.tsx
│   │   │   ├── AudioChunkedContent.tsx
│   │   │   ├── AudioExtractionJobsTable.tsx
│   │   │   ├── AudioFilesTable.tsx
│   │   │   ├── AudioPlayer.tsx
│   │   │   ├── AudioProjectCard.tsx
│   │   │   ├── AudioRatingBreakdownRow.tsx
│   │   │   ├── FormattedRawResult.tsx
│   │   │   ├── NewAudioProjectModal.tsx
│   │   │   └── UploadAudioModal.tsx
│   │   ├── hooks/               # Audio-related hooks
│   │   │   └── useAudioExtractionJobPolling.ts
│   │   ├── projects/            # Audio project pages
│   │   │   └── [projectId]/
│   │   │       ├── audios/
│   │   │       │   └── [audioId]/
│   │   │       │       └── extractors/
│   │   │       │           ├── components/
│   │   │       │           │   ├── AudioAnnotationsListTab.tsx
│   │   │       │           │   ├── AudioAnnotationTab.tsx
│   │   │       │           │   ├── AudioExtractorsHeader.tsx
│   │   │       │           │   └── AudioSummaryTab.tsx
│   │   │       │           └── page.tsx
│   │   │       └── page.tsx
│   │   ├── page.tsx             # Audio projects dashboard
│   │   └── utils.ts             # Audio utility functions
│   ├── components/              # Reusable components
│   │   ├── ui/                  # shadcn/ui components (19 components)
│   │   │   ├── alert.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── checkbox.tsx
│   │   │   ├── confirmation-dialog.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── select.tsx
│   │   │   ├── sonner.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── toaster.tsx
│   │   │   ├── tooltip.tsx
│   │   │   └── useToast.ts
│   │   ├── AnnotatableText.tsx  # Text annotation component
│   │   ├── ChangePasswordModal.tsx
│   │   ├── DynamicModals.tsx    # Lazy-loaded modal components
│   │   ├── ErrorBoundary.tsx    # Error boundary component
│   │   ├── JsonViewer.tsx        # JSON content viewer
│   │   ├── Layout.tsx           # Main application layout
│   │   ├── LoginForm.tsx        # Authentication forms
│   │   ├── ProtectedRoute.tsx   # Route protection wrapper
│   │   └── Sidebar.tsx          # Navigation sidebar
│   ├── constants/               # Centralized constants
│   │   └── index.ts             # App-wide constants (API, polling, pagination, etc.)
│   ├── contexts/                # React contexts
│   │   ├── AuthContext.tsx      # Authentication state management
│   │   └── SidebarContext.tsx   # Sidebar state management
│   ├── document/                # Document (PDF) extraction feature
│   │   ├── components/          # Document-specific components
│   │   │   ├── documents/       # Document table components
│   │   │   │   ├── DocumentsTable.tsx
│   │   │   │   ├── UploadFileModal.tsx
│   │   │   │   └── index.ts
│   │   │   ├── extractors/      # Extractor-related components
│   │   │   │   ├── AnnotationPanel.tsx
│   │   │   │   ├── AnnotationsListTable.tsx
│   │   │   │   ├── ContentDisplay.tsx
│   │   │   │   ├── ContentViewSelector.tsx
│   │   │   │   ├── DynamicComponents.tsx (code splitting)
│   │   │   │   ├── ExtractionJobsTable.tsx
│   │   │   │   ├── ExtractorHeader.tsx
│   │   │   │   ├── ExtractorSelector.tsx
│   │   │   │   ├── ImagesRenderer.tsx (optimized with Next.js Image)
│   │   │   │   ├── ImageViewer.tsx
│   │   │   │   ├── LatexRenderer.tsx
│   │   │   │   ├── MarkdownRenderer.tsx
│   │   │   │   ├── PageNavigation.tsx
│   │   │   │   ├── PDFViewer.tsx
│   │   │   │   ├── RatingBreakdownRow.tsx
│   │   │   │   ├── RatingControl.tsx
│   │   │   │   ├── RatingSection.tsx
│   │   │   │   └── index.ts
│   │   │   ├── new-project/     # New project creation
│   │   │   │   ├── ExtractionKeyForm.tsx
│   │   │   │   ├── ExtractionKeyList.tsx
│   │   │   │   ├── NewProjectModal.tsx
│   │   │   │   └── index.ts
│   │   │   ├── project-card/    # Project card component
│   │   │   │   ├── ProjectCard.tsx
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── hooks/               # Document-related hooks (5 custom hooks)
│   │   │   ├── useExtractionJobPolling.ts (uses constants)
│   │   │   ├── useImageViewer.ts
│   │   │   ├── usePageContent.ts
│   │   │   ├── usePDFViewer.ts
│   │   │   ├── useSecureImage.ts
│   │   │   └── index.ts
│   │   ├── projects/            # Document project pages
│   │   │   └── [projectId]/
│   │   │       ├── documents/
│   │   │       │   └── [documentId]/
│   │   │       │       └── extractors/
│   │   │       │           └── page.tsx
│   │   │       └── page.tsx
│   │   ├── types/               # TypeScript definitions
│   │   │   └── index.ts
│   │   ├── utils/               # Helper functions
│   │   │   ├── content-helpers.ts
│   │   │   ├── formatters.ts
│   │   │   ├── status-helpers.ts
│   │   │   └── index.ts
│   │   └── page.tsx             # Document projects dashboard
│   ├── hooks/                   # Global custom React hooks
│   │   └── useToast.ts
│   ├── image/                   # Image OCR extraction feature
│   │   ├── components/         # Image-specific components
│   │   │   ├── ImageAnnotationsListTable.tsx
│   │   │   ├── ImageExtractionJobsTable.tsx
│   │   │   ├── ImageFilesTable.tsx
│   │   │   ├── ImageProjectCard.tsx
│   │   │   ├── ImageRatingBreakdownRow.tsx
│   │   │   ├── NewImageProjectModal.tsx
│   │   │   └── UploadImageModal.tsx
│   │   ├── hooks/               # Image-related hooks
│   │   │   └── useImageExtractionJobPolling.ts
│   │   ├── projects/            # Image project pages
│   │   │   └── [projectId]/
│   │   │       ├── images/
│   │   │       │   └── [imageId]/
│   │   │       │       └── extractors/
│   │   │       │           ├── components/
│   │   │       │           │   ├── ImageAnnotationsListTab.tsx
│   │   │       │           │   ├── ImageAnnotationTab.tsx
│   │   │       │           │   ├── ImageExtractorsHeader.tsx
│   │   │       │           │   └── ImageSummaryTab.tsx
│   │   │       │           └── page.tsx
│   │   │       └── page.tsx
│   │   ├── page.tsx             # Image projects dashboard
│   │   └── utils.ts             # Image utility functions
│   ├── lib/                     # Utility functions
│   │   ├── api-utils.ts         # API retry logic, timeout, error handling
│   │   └── utils.ts             # General utilities
│   ├── services/                # API services
│   │   ├── api.ts               # Backend API client (documents) with retry logic
│   │   ├── audioApi.ts          # Audio API client
│   │   └── imageApi.ts          # Image API client
│   ├── types/                   # Shared TypeScript types
│   │   ├── index.ts             # Barrel export
│   │   └── shared.ts            # Common type definitions
│   ├── globals.css              # Global styles
│   ├── layout.tsx               # Root layout
│   ├── page.tsx                 # Home page (redirects to /document)
│   ├── not-found.tsx            # 404 page
│   └── providers.tsx            # Client providers (React Query)
├── public/                      # Static assets
│   ├── favicon.ico
│   ├── logo.png
│   ├── placeholder.svg
│   └── robots.txt
├── components.json              # shadcn/ui configuration
├── tailwind.config.ts           # Tailwind CSS configuration
├── next.config.js               # Next.js configuration
├── postcss.config.js            # PostCSS configuration
├── tsconfig.json                # TypeScript configuration
└── package.json                 # Dependencies and scripts
```

## 🚦 Getting Started

### Prerequisites

- Node.js 18+ 
- npm, yarn, or pnpm
- Backend API running (see backend documentation)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd pdf-extraction-tool/frontend
```

2. **Install dependencies**:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. **Configure environment variables**:
Create a `.env.local` file in the frontend directory:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. **Run the development server**:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

5. **Open your browser**:
Navigate to [http://localhost:3000](http://localhost:3000)

## 📱 Key Pages & Features

### Authentication
- **Login/Signup** (`/`): Secure authentication with admin approval workflow (redirects to `/document` after login)
- **Protected Routes**: All pages require authentication and appropriate permissions

### Project Management
- **Home Page** (`/`): Redirects to document projects dashboard
- **Document Projects Dashboard** (`/document`): Overview of all document projects with creation and management
- **New Document Project**: Create new document extraction projects with configuration
- **Document Project Detail** (`/document/projects/[projectId]`): View project performance, documents, and settings
- **Audio Projects Dashboard** (`/audio`): Overview of all audio transcription projects
- **Image Projects Dashboard** (`/image`): Overview of all image OCR projects

### Document Processing
- **Document Upload**: Drag-and-drop file upload with multiple extraction engine selection
- **Document Viewer** (`/document/projects/[projectId]/documents/[documentId]/extractors`): 
  - Side-by-side PDF and extracted content viewing
  - Interactive annotation system
  - Quality rating and feedback
  - Multiple extraction engine results comparison
  - Support for text, markdown, LaTeX, and JSON content formats
  - Page-by-page navigation
  - Content view selector (text, markdown, LaTeX, images)

### Audio Processing
- **Audio Projects** (`/audio`): Create and manage audio transcription projects
- **Audio Upload**: Upload audio files (MP3, WAV, etc.) for transcription
- **Audio Viewer** (`/audio/projects/[projectId]/audios/[audioId]/extractors`):
  - View transcribed content with timestamps
  - Audio player with playback controls
  - Chunked content display
  - Annotation system
  - Quality rating and feedback
- **Multiple Engines**: Choose from Whisper, AssemblyAI, or AWS Transcribe
- **Real-time Monitoring**: Track transcription job progress

### Image Processing
- **Image Projects** (`/image`): Create and manage image OCR projects
- **Image Upload**: Upload image files for text extraction
- **Image Viewer** (`/image/projects/[projectId]/images/[imageId]/extractors`):
  - View extracted text from images
  - Image display with extracted content
  - Annotation system
  - Quality rating and feedback
- **Multiple Engines**: Choose from Tesseract, Textract, Mathpix, OpenAI, or Azure

### Admin Panel
- **User Management** (`/admin`): 
  - Approve pending user registrations
  - Activate/deactivate user accounts
  - Reset user passwords
  - View user roles and status

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## 🔐 Authentication Flow

1. **User Registration**: Users sign up and are placed in "pending" status
2. **Admin Approval**: Administrators approve users through the admin panel
3. **Login Access**: Only approved and active users can log in
4. **Role-Based Access**: Admin users have access to user management features

## 🎨 UI Components

Built with shadcn/ui components for consistency and accessibility:
- Form components (Input, Button, Select, etc.)
- Layout components (Card, Dialog, Sheet, etc.)
- Feedback components (Toast, Alert, etc.)
- Navigation components (Tabs, Dropdown, etc.)

## 🌐 API Integration

The frontend communicates with the backend through comprehensive API clients that handle:
- **Authentication and user management** (`services/api.ts`)
- **Document operations** (`services/api.ts`)
- **Audio operations** (`services/audioApi.ts`)
- **Image operations** (`services/imageApi.ts`)
- **Extraction job monitoring** with real-time polling
- **File uploads and downloads**
- **Admin operations**

### API Reliability Features
- **Automatic Retry Logic**: Failed requests retry up to 2 times with exponential backoff
- **Request Timeout**: 30-second timeout prevents hanging requests
- **Request Deduplication**: GET requests are cached to prevent duplicate calls
- **Enhanced Error Handling**: Detailed error messages with status codes
- **Configurable via** `app/constants/index.ts`

## ⚡ Performance Optimizations

The application includes several performance optimizations:

### Code Splitting
- **Dynamic Imports**: Heavy components (LaTeX renderer, PDF viewer, modals) are lazy-loaded
- **Reduced Initial Bundle**: Smaller initial JavaScript payload
- **On-Demand Loading**: Components load only when needed

### Image Optimization
- **Next.js Image Component**: Automatic image optimization with lazy loading
- **Secure Image Loading**: Custom hook for authenticated image requests

### Error Handling
- **Error Boundaries**: Graceful error handling prevents app crashes
- **Development vs Production**: Detailed errors in dev, user-friendly messages in production
- **Component Isolation**: Errors in one component don't affect others

### State Management
- **TanStack Query**: Intelligent caching and background refetching
- **Request Deduplication**: Prevents redundant API calls
- **Optimistic Updates**: Instant UI feedback with server synchronization

### Constants & Configuration
- **Centralized Configuration**: Single source of truth in `app/constants/index.ts`
- **Easy Maintenance**: Update polling intervals, timeouts, and limits in one place
- **Type-Safe**: Full TypeScript support for all constants

## 🚀 Deployment

### Production Build
```bash
npm run build
npm run start
```

### Docker Deployment
```bash
# Build Docker image
docker build -t pdf-extraction-frontend .

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  pdf-extraction-frontend
```

### Docker Compose
The frontend is included in the main `docker-compose.yml` file and will start automatically with:
```bash
docker-compose up --build
```

### Environment Variables
Ensure the following environment variables are set:
- `NEXT_PUBLIC_API_URL`: Backend API URL (e.g., `http://localhost:8000`)

For production, set:
- `NEXT_PUBLIC_API_URL`: Production backend API URL

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and test thoroughly
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Guidelines

- **TypeScript**: Follow TypeScript best practices and maintain type safety
- **Components**: Use the existing component library (shadcn/ui) for consistency
- **Code Organization**:
  - Place reusable components in `app/components/`
  - Use feature-specific folders for domain logic
  - Centralize constants in `app/constants/`
  - Define shared types in `app/types/`
- **Performance**:
  - Use dynamic imports for large components
  - Optimize images with Next.js Image component
  - Implement proper error boundaries
- **State Management**: Use TanStack Query for server state
- **API Integration**: Use the centralized API service with retry logic
- **Commit Messages**: Write clear, meaningful commit messages
- **Testing**: Test your changes thoroughly before submitting
- **Responsive Design**: Ensure mobile and desktop compatibility
- **Code Style**: Follow the existing patterns and conventions

## 🏗️ Architecture Highlights

### Component Decomposition
Large, complex pages have been decomposed into smaller, focused components:
- **ExtractorHeader**: Project and document navigation
- **ContentDisplay**: Handles multiple content rendering modes
- **RatingSection**: Rating UI and average display

### API Layer
- **Enhanced Fetch**: Wrapper with retry, timeout, and deduplication
- **Error Handling**: Structured error responses with status codes
- **Type Safety**: Full TypeScript coverage for all API responses

### File Organization
```
Feature-based structure:
document/
  ├── components/    # UI components
  ├── hooks/         # Custom React hooks
  ├── types/         # TypeScript definitions
  ├── utils/         # Helper functions
  └── projects/      # Project pages

audio/
  ├── components/    # Audio-specific components
  ├── hooks/         # Audio-related hooks
  ├── projects/      # Audio project pages
  └── utils.ts       # Audio utilities

image/
  ├── components/    # Image-specific components
  ├── hooks/         # Image-related hooks
  ├── projects/      # Image project pages
  └── utils.ts       # Image utilities

Shared resources:
├── components/     # Reusable UI components
├── constants/      # App-wide configuration
├── contexts/       # React contexts
├── hooks/          # Global hooks
├── lib/            # Utility functions
├── services/       # API clients
└── types/          # Shared type definitions
```

## 📄 License

MIT License - see [LICENSE](../../LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the backend documentation for API details
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join community discussions for questions and ideas

---

Built with ❤️ using Next.js, TypeScript, and modern web technologies.