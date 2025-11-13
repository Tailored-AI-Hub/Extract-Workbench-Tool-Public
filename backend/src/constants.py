import os
from dotenv import load_dotenv

load_dotenv()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

def is_s3_available() -> bool:
    """Check if S3 is configured and available"""
    return bool(AWS_BUCKET_NAME and AWS_REGION)

TOPK = 3
RETRY = 1

EMBEDDING_DIMENSION = 1536
EMBEDDING_BATCH_SIZE = 20
BATCH_SIZE = 100

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)
COHERE_API_KEY = os.getenv('COHERE_API_KEY', None)
LLAMAPARSE_API_KEY = os.getenv('LLAMAPARSE_API_KEY')
NANONETS_API_KEY = os.getenv('NANONETS_API_KEY')

REDIS_BROKER_URL = os.getenv("REDIS_BROKER_URL", "redis://redis:6379/0")
REDIS_BACKEND_URL = os.getenv("REDIS_BACKEND_URL", "redis://redis:6379/1")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "pdf-extraction-db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pdf_extraction")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct database URLs from environment variables
# Handle case where no password is set
if DB_PASSWORD:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

MATHPIX_APP_ID = os.getenv('MATHPIX_APP_ID')
MATHPIX_APP_KEY = os.getenv('MATHPIX_APP_KEY')

# Azure Document Intelligence
AZURE_DI_ENDPOINT = os.getenv('AZURE_DI_ENDPOINT')
AZURE_DI_KEY = os.getenv('AZURE_DI_KEY')

# Auth/JWT
# Backwards-compatible secret key envs
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days

# Admin basic-auth credentials for admin endpoints
ADMIN_NAME = os.getenv("ADMIN_NAME")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "/app/uploads")
# Shared volume and stage configuration
STAGE = os.getenv("STAGE", "development")
SHARED_VOLUME_PATH = os.getenv("SHARED_VOLUME_PATH", "/app/shared_volume")

# Stage-dependent configs
if STAGE == "production":
    FILE_CLEANUP_TTL_SECONDS = 21600  # 6 hours
    CLEANUP_ON_TASK_FAILURE = False
else:
    FILE_CLEANUP_TTL_SECONDS = 7200  # 2 hours
    CLEANUP_ON_TASK_FAILURE = True

# Celery retry configurations by extractor type
EXTRACTOR_RETRY_CONFIG = {
    # Simple PDF extractors - fail fast
    "PyPDF2": {"max_retries": 1, "countdown": 5},
    "PyMuPDF": {"max_retries": 1, "countdown": 5},
    "PDFPlumber": {"max_retries": 1, "countdown": 5},
    
    # Medium complexity extractors
    "Tesseract": {"max_retries": 2, "countdown": 10},
    # "Camelot": {"max_retries": 2, "countdown": 10},  # Disabled - causing failures
    # "Tabula": {"max_retries": 2, "countdown": 10},  # Disabled - causing failures
    
    # API-based extractors - allow more retries
    "gpt-4o-mini": {"max_retries": 3, "countdown": 30},
    "gpt-4o": {"max_retries": 3, "countdown": 30},
    "gpt-5": {"max_retries": 3, "countdown": 30},
    "gpt-5-mini": {"max_retries": 3, "countdown": 30},
    "Textract": {"max_retries": 3, "countdown": 30},
    "Mathpix": {"max_retries": 3, "countdown": 30},
    "LlamaParse": {"max_retries": 3, "countdown": 30},
    "MarkItDown": {"max_retries": 2, "countdown": 10},
    # "Unstructured": {"max_retries": 2, "countdown": 10},  # Disabled - causing failures
}

# Default for unknown extractors
DEFAULT_RETRY_CONFIG = {"max_retries": 2, "countdown": 10}

# Circuit breaker settings
CIRCUIT_BREAKER_THRESHOLD = 50  # consecutive failures before breaking
CIRCUIT_BREAKER_TIMEOUT = 10  # seconds before resetting circuit

# Langfuse configuration for cost tracking
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")