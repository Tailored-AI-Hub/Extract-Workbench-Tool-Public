# PDF Extraction Tool - Backend

A robust FastAPI-based backend service for AI-powered document extraction, featuring multiple extraction engines, user management, and real-time processing capabilities.

## 🚀 Features

### Core Functionality
- **Multi-Engine PDF Processing**: Support for 13+ extraction engines with different strengths
- **Async Document Processing**: Celery-based background job processing with Redis
- **Real-time Status Tracking**: Live updates on extraction progress and results
- **Project Management**: Organize documents into projects with detailed metadata
- **File Storage**: AWS S3 integration for scalable document storage

### User Management & Security
- **Admin Approval Workflow**: New users require admin approval before access
- **JWT Authentication**: Secure token-based authentication with role validation
- **Role-Based Access Control**: Admin and user roles with appropriate permissions
- **User Management API**: Complete CRUD operations for user administration

### Extraction Engines
- **PDF Processing**: 14+ extraction engines (PyPDF2, PyMuPDF, PDFPlumber, Camelot, Tabula, Tesseract, Textract, Mathpix, Unstructured, OpenAI GPT models, MarkItDown, LlamaParse, Azure Document Intelligence)
- **Audio Transcription**: 3 engines (Whisper OpenAI, AssemblyAI, AWS Transcribe)
- **Image OCR**: 5 engines (Tesseract, Textract, Mathpix, OpenAI GPT-4o, Azure Document Intelligence)
- **Cost Tracking**: Per-page/per-minute pricing for each extraction engine

## 🛠 Tech Stack

- **Framework**: FastAPI with async/await support
- **Language**: Python 3.12+
- **Database**: PostgreSQL (production) / SQLite (development) with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT with PassLib for password hashing
- **File Storage**: AWS S3 (optional)
- **API Documentation**: Automatic OpenAPI/Swagger generation

## 📁 Project Structure

```
backend/
├── src/
│   ├── auth/                    # Authentication module
│   │   ├── routes.py           # Auth endpoints (login, signup, admin)
│   │   └── security.py         # JWT and password utilities
│   ├── extractors_document/    # PDF extraction engine implementations
│   │   ├── camelot_extractor.py
│   │   ├── llamaparse.py
│   │   ├── markitdown_extractor.py
│   │   ├── mathpix_extractor.py
│   │   ├── pdfplumber_extractor.py
│   │   ├── pymupdf_extractor.py
│   │   ├── pypdf2_extractor.py
│   │   ├── tabula_extractor.py
│   │   ├── tesseract_extractor.py
│   │   ├── textract_extractor.py
│   │   ├── unstructured_extractor.py
│   │   ├── openai_vision_extractor.py
│   │   ├── azure_extractor.py
│   │   ├── factory.py          # PDF extractor factory
│   │   └── interface.py        # PDF extraction interface
│   ├── extractor_audio/        # Audio transcription engines
│   │   ├── whisper_openai_extractor.py
│   │   ├── assemblyai_extractor.py
│   │   ├── aws_transcribe_extractor.py
│   │   ├── factory.py          # Audio extractor factory
│   │   └── interface.py        # Audio extraction interface
│   ├── extractor_image/        # Image OCR engines
│   │   ├── tesseract_extractor.py
│   │   ├── textract_extractor.py
│   │   ├── mathpix_extractor.py
│   │   ├── openai_vision_extractor.py
│   │   ├── azure_extractor.py
│   │   ├── factory.py          # Image extractor factory
│   │   └── interface.py        # Image extraction interface
│   ├── models/                 # Database models and schemas
│   │   ├── database.py         # SQLAlchemy models
│   │   ├── schemas.py          # Pydantic schemas
│   │   └── enums.py            # Enum definitions
│   ├── factory/                # Factory modules
│   │   ├── pdf.py              # PDF extractor factory
│   │   └── audio.py            # Audio extractor factory
│   ├── tests/                  # Test suite
│   ├── constants.py            # Configuration constants
│   ├── db.py                   # Database connection
│   ├── file_coordinator.py     # File management utilities
│   ├── main.py                 # FastAPI application entry point
│   ├── tasks.py                # Celery task definitions
│   └── worker.py               # Celery worker configuration
├── tests/                      # Test suite
├── compose.yaml                # Docker Compose configuration
├── Dockerfile                  # Container configuration
├── pyproject.toml              # Project configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚦 Getting Started

### Prerequisites

- Python 3.12+
- Redis server
- [UV package manager](https://docs.astral.sh/uv/) (recommended)
- AWS credentials (optional, for S3 storage)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd pdf-extraction-tool/backend
```

2. **Install UV** (if not already installed):
```bash
pip3 install uv
```

3. **Install dependencies**:
```bash
uv sync
```

4. **Configure environment variables**:
Create a `.env` file in the backend directory:
```bash
# Database
DATABASE_URL=sqlite:///./pdf-extraction.db

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Admin credentials
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your-secure-password

# Redis (for Celery)
REDIS_BROKER_URL=redis://localhost:6379/0
REDIS_BACKEND_URL=redis://localhost:6379/1

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your-bucket-name

# OpenAI (for GPT extractors)
OPENAI_API_KEY=your-openai-api-key

# Mathpix (optional)
MATHPIX_APP_ID=your-app-id
MATHPIX_APP_KEY=your-app-key

# LlamaParse (optional)
LLAMAPARSE_API_KEY=your-llamaparse-key
```

5. **Run database migration**:
```bash
python run_migration.py
```

6. **Start Redis server**:
```bash
redis-server
```

7. **Start the FastAPI server**:
```bash
# Production mode
uv run gunicorn src.main:app \
    -k uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000

# Development mode (with hot reload)
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Start the Celery worker** (in a separate terminal):
```bash
celery -A src.tasks.celery_app worker --loglevel=info -P solo
```

9. **Access the API**:
- API: [http://localhost:8000](http://localhost:8000)
- Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🔧 Extraction Engines

### PDF Processing Libraries

#### PyPDF2
- **Description**: Pure Python PDF toolkit for reading, splitting, merging, and cropping PDFs
- **Best for**: Basic text extraction, document manipulation
- **Documentation**: [PyPDF2 Documentation](https://pypdf2.readthedocs.io/)
- **Cost**: Free

#### PyMuPDF (fitz)
- **Description**: High-performance PDF and image processing library
- **Best for**: Fast text extraction, image rendering, advanced PDF features
- **Documentation**: [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- **Cost**: Free

#### PDFPlumber
- **Description**: Plumb a PDF for detailed information about each text character, rectangle, and line
- **Best for**: Precise text extraction, table detection, layout analysis
- **Documentation**: [PDFPlumber Documentation](https://github.com/jsvine/pdfplumber)
- **Cost**: Free

### Table Extraction

#### Camelot
- **Description**: Python library for extracting tables from PDFs
- **Best for**: Structured table data extraction
- **Documentation**: [Camelot Documentation](https://camelot-py.readthedocs.io/)
- **Cost**: Free

#### Tabula
- **Description**: Extract tables from PDFs using Java-based Tabula
- **Best for**: Complex table structures, CSV export
- **Documentation**: [Tabula Documentation](https://tabula-py.readthedocs.io/)
- **Cost**: Free

### OCR Engines

#### Tesseract
- **Description**: Open source OCR engine for text recognition
- **Best for**: Scanned documents, image-based PDFs
- **Documentation**: [Tesseract Documentation](https://tesseract-ocr.github.io/)
- **Cost**: Free

#### AWS Textract
- **Description**: Amazon's machine learning service for text and data extraction
- **Best for**: High-accuracy OCR, form processing, table extraction
- **Documentation**: [AWS Textract Documentation](https://docs.aws.amazon.com/textract/)
- **Cost**: Pay-per-page

### AI-Powered Extractors

#### OpenAI GPT Models
- **Description**: GPT-4, GPT-4o, and GPT-5 models for intelligent document understanding
- **Best for**: Complex document analysis, semantic extraction, content summarization
- **Documentation**: [OpenAI API Documentation](https://platform.openai.com/docs)
- **Cost**: Pay-per-token

#### Mathpix
- **Description**: AI-powered math and science content recognition
- **Best for**: Mathematical equations, scientific formulas, LaTeX conversion
- **Documentation**: [Mathpix API Documentation](https://mathpix.com/docs)
- **Cost**: Pay-per-request

#### Unstructured
- **Description**: Open source library for extracting structured data from documents
- **Best for**: Document parsing, content chunking, metadata extraction
- **Documentation**: [Unstructured Documentation](https://unstructured-io.github.io/unstructured/)
- **Cost**: Free

#### MarkItDown
- **Description**: Microsoft's universal document converter
- **Best for**: Converting various document formats to Markdown
- **Documentation**: [MarkItDown Documentation](https://github.com/microsoft/markitdown)
- **Cost**: Free

#### LlamaParse
- **Description**: LlamaIndex's intelligent document parsing service
- **Best for**: RAG-optimized document parsing, semantic understanding
- **Documentation**: [LlamaParse Documentation](https://docs.llamaindex.ai/en/stable/examples/data_connectors/LlamaParse/)
- **Cost**: Pay-per-page

#### Azure Document Intelligence
- **Description**: Microsoft's AI-powered document processing service
- **Best for**: Enterprise document processing, form recognition, invoice processing
- **Documentation**: [Azure Document Intelligence Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- **Cost**: Pay-per-page

### Audio Transcription Engines

#### Whisper (OpenAI)
- **Description**: OpenAI's state-of-the-art speech recognition model
- **Best for**: High-accuracy transcription, multiple languages, speaker diarization
- **Documentation**: [OpenAI Whisper Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- **Cost**: Pay-per-minute

#### AssemblyAI
- **Description**: Production-ready speech-to-text API with advanced features
- **Best for**: Real-time transcription, speaker diarization, sentiment analysis
- **Documentation**: [AssemblyAI Documentation](https://www.assemblyai.com/docs)
- **Cost**: Pay-per-minute

#### AWS Transcribe
- **Description**: Amazon's automatic speech recognition service
- **Best for**: Scalable transcription, multiple languages, custom vocabularies
- **Documentation**: [AWS Transcribe Documentation](https://docs.aws.amazon.com/transcribe/)
- **Cost**: Pay-per-minute

### Image OCR Engines

#### Tesseract (Image)
- **Description**: Open source OCR engine for text recognition from images
- **Best for**: Text extraction from images, scanned documents
- **Documentation**: [Tesseract Documentation](https://tesseract-ocr.github.io/)
- **Cost**: Free

#### AWS Textract (Image)
- **Description**: Amazon's machine learning service for text extraction from images
- **Best for**: High-accuracy image OCR, form processing
- **Documentation**: [AWS Textract Documentation](https://docs.aws.amazon.com/textract/)
- **Cost**: Pay-per-page

#### Mathpix (Image)
- **Description**: AI-powered math and science content recognition from images
- **Best for**: Mathematical equations in images, scientific formulas
- **Documentation**: [Mathpix API Documentation](https://mathpix.com/docs)
- **Cost**: Pay-per-request

#### OpenAI GPT-4o (Image)
- **Description**: GPT-4o vision model for image understanding and text extraction
- **Best for**: Complex image analysis, text extraction, visual understanding
- **Documentation**: [OpenAI Vision Documentation](https://platform.openai.com/docs/guides/vision)
- **Cost**: Pay-per-image

#### Azure Document Intelligence (Image)
- **Description**: Microsoft's AI service for document image processing
- **Best for**: Document images, form recognition, invoice processing
- **Documentation**: [Azure Document Intelligence Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- **Cost**: Pay-per-page

## 🔐 Authentication & Authorization

### User Registration Flow
1. User signs up with email/password
2. Account created with `is_approved=False`
3. Admin approves user via `/auth/admin/approve/{user_id}`
4. User can now log in and access the platform

### API Endpoints

#### Authentication
- `POST /auth/signup` - User registration (returns success message, no token)
- `POST /auth/login` - User login (returns JWT token)
- `GET /auth/me` - Get current user profile

#### Admin Management (requires admin role)
- `GET /auth/admin/users` - List all users
- `POST /auth/admin/approve/{user_id}` - Approve user
- `POST /auth/admin/activate/{user_id}` - Activate user
- `POST /auth/admin/deactivate/{user_id}` - Deactivate user
- `POST /auth/admin/reset-password/{user_id}` - Reset user password

#### Document Processing
- `POST /projects/{project_uuid}/upload` - Upload single document
- `POST /projects/{project_uuid}/upload-multiple` - Upload multiple documents
- `GET /projects/{project_uuid}/documents` - List project documents
- `GET /projects/{project_uuid}/documents/{document_uuid}/extraction-jobs` - Get extraction jobs
- `GET /projects/{project_uuid}/documents/{document_uuid}/extractors/{extractor_type}/pages/{page_number}/content` - Get page content

#### Audio Processing
- `POST /audio/projects` - Create audio project
- `POST /audio/projects/{project_id}/upload` - Upload audio file
- `GET /audio/projects/{project_id}/files` - List audio files
- `GET /audio/projects/{project_id}/extraction-jobs` - Get extraction jobs
- `GET /audio/projects/{project_id}/files/{file_id}/content` - Get transcription content

#### Image Processing
- `POST /image/projects` - Create image project
- `POST /image/projects/{project_id}/upload` - Upload image file
- `GET /image/projects/{project_id}/files` - List image files
- `GET /image/projects/{project_id}/extraction-jobs` - Get extraction jobs

## 🗄️ Database Schema

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `hashed_password`: PBKDF2 hashed password
- `is_active`: Account active status
- `is_approved`: Admin approval status
- `role`: User role (admin/user)
- `name`: User display name
- `organization_name`: Optional organization
- `organization_id`: Optional organization ID

### Projects Table
- `uuid`: Project identifier
- `name`: Project name
- `description`: Project description
- `user_id`: Owner user ID
- `created_at`: Creation timestamp

### Documents Table
- `uuid`: Document identifier
- `filename`: Original filename
- `filepath`: Storage path
- `page_count`: Number of pages
- `file_type`: File type (pdf/image/audio)
- `project_uuid`: Parent project
- `user_id`: Owner user ID

### Extraction Jobs Table
- `uuid`: Job identifier
- `document_uuid`: Associated document
- `extractor_type`: Extraction engine used
- `status`: Job status (Not Started, Processing, Success, Failure)
- `created_at`: Creation timestamp
- `completed_at`: Completion timestamp
- `error_message`: Error details if failed

### Page Content Table
- `id`: Primary key
- `document_uuid`: Associated document
- `extractor_type`: Extraction engine used
- `page_number`: Page number
- `content`: Extracted content (text/markdown/JSON)
- `metadata`: Additional metadata

## 🚀 Deployment

### Docker Deployment

#### Development
```bash
# Build and run with docker-compose
docker-compose up --build
```

#### Production
```bash
# Build and run production services
docker-compose -f docker-compose-prod.yml up --build -d
```

The Docker setup includes:
- **API Service**: FastAPI backend with Gunicorn
- **Worker Service**: Celery worker for background processing
- **PostgreSQL**: Database service
- **Redis**: Task queue broker and result backend

### Production Considerations
- **Database**: Use PostgreSQL instead of SQLite for production
- **Redis**: Configure Redis clustering for high availability
- **Storage**: Set up AWS S3 for scalable file storage
- **Configuration**: Use environment-specific configuration files
- **Monitoring**: Implement proper logging and monitoring (e.g., Prometheus, Grafana)
- **Security**: Set up SSL/TLS termination (nginx reverse proxy)
- **Scaling**: Run multiple Celery workers for parallel processing
- **Backup**: Implement regular database backups
- **CORS**: Configure CORS properly for production domains

## 🧪 Testing

Run the test suite:
```bash
uv run pytest tests/ -v --cov=src
```

## 📊 Monitoring

### Health Checks
- `GET /` - Basic health check
- `GET /extractors` - Available extraction engines

### Metrics
- Extraction job status tracking
- Processing time metrics
- Cost tracking per extraction engine
- User activity monitoring

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run tests**: `uv run pytest tests/ -v`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write comprehensive tests
- Update documentation for new features
- Use async/await for I/O operations

## 📄 License

MIT License - see [LICENSE](../../LICENSE) file for details.

## 🆘 Support

- **API Documentation**: Available at `/docs` endpoint
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join community discussions

---

Built with ❤️ using FastAPI, Python, and modern async technologies.