import uuid
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, inspect
from typing import AsyncGenerator
from loguru import logger
from pathlib import Path
from urllib.parse import urlparse
import httpx
from src.db import get_db, engine_async, Base
from src.models import User
from src.auth.routes import router as auth_router
from src.auth.security import hash_password
from src.constants import (
    STAGE,
    UPLOADS_DIR,
    ADMIN_NAME,
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    AWS_REGION,
    DATABASE_URL
)
from contextlib import asynccontextmanager
from sqlalchemy.exc import OperationalError
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect
from alembic.script import ScriptDirectory  # type: ignore
from alembic.runtime.migration import MigrationContext  # type: ignore
# Import routers
from src.routes import pdf, audio, image

# Resolve project root and uploads directory absolutely so static mount works
# main.py lives in backend/src; the repo root is two levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan handler - executed once at startup and once at shutdown.
    """
    # --------------------------------------------------------------------- #
    # 1. STARTUP
    # --------------------------------------------------------------------- #
    logger.info("Application starting - initialising database...")
    
    # ----- 1.0 Run Alembic migrations first (if any) ----- #
    try:
        # Find alembic.ini - could be in backend/ or root (Docker uses /app)
        alembic_ini_path = Path("alembic.ini")
        if not alembic_ini_path.exists():
            alembic_ini_path = Path("backend/alembic.ini")
        if not alembic_ini_path.exists():
            alembic_ini_path = Path("/app/alembic.ini")  # Docker path
        if alembic_ini_path.exists():
            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
            
            # Create a synchronous engine for Alembic operations
            sync_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            
            with sync_engine.connect() as connection:
                # Get script directory to check migration status
                script_dir = ScriptDirectory.from_config(alembic_cfg)
                
                # Check current migration status
                migration_context = MigrationContext.configure(connection)
                current_revision = migration_context.get_current_revision()
                head_revision = script_dir.get_current_head()
                
                logger.info(f"Current database revision: {current_revision or 'None (no migrations applied)'}")
                logger.info(f"Target revision (head): {head_revision or 'None'}")
                
                # Check schema compliance
                inspector = sqlalchemy_inspect(connection)
                existing_tables = set(inspector.get_table_names())
                required_tables = set(Base.metadata.tables.keys())
                
                missing_tables = required_tables - existing_tables
                extra_tables = existing_tables - required_tables
                
                # Check for missing columns in existing tables
                schema_differences = []
                for table_name in existing_tables & required_tables:
                    table = Base.metadata.tables[table_name]
                    db_columns = {col['name'] for col in inspector.get_columns(table_name)}
                    model_columns = {col.name for col in table.columns}
                    
                    missing_cols = model_columns - db_columns
                    if missing_cols:
                        schema_differences.append({
                            'table': table_name,
                            'missing_columns': list(missing_cols)
                        })
                
                # Log schema status
                if missing_tables:
                    logger.info(f"Missing tables detected: {missing_tables}")
                if extra_tables:
                    logger.debug(f"Extra tables in database (non-critical): {extra_tables}")
                if schema_differences:
                    for diff in schema_differences:
                        logger.info(f"Table '{diff['table']}' missing columns: {diff['missing_columns']}")
                
                # Determine if migrations are needed
                needs_migration = False
                if current_revision is None:
                    # No migrations applied yet
                    if head_revision is not None:
                        needs_migration = True
                        logger.info("No migrations applied - will run migrations to head")
                elif current_revision != head_revision:
                    # Behind target revision
                    needs_migration = True
                    logger.info(f"Database is behind target revision - will upgrade from {current_revision} to {head_revision}")
                elif missing_tables or schema_differences:
                    # Schema doesn't match models - migrations might fix it
                    needs_migration = True
                    logger.info("Schema differences detected - will run migrations to ensure compliance")
                else:
                    logger.info("Database schema is compliant and up-to-date - no migrations needed")
                
                # Only run migrations if needed
                if needs_migration:
                    logger.info("Running database migrations...")
                    # Use Alembic's upgrade command
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Database migrations completed successfully")
                    
                    # Verify schema compliance after migration
                    with sync_engine.connect() as verify_conn:
                        verify_inspector = sqlalchemy_inspect(verify_conn)
                        verify_tables = set(verify_inspector.get_table_names())
                        verify_missing = required_tables - verify_tables
                        
                        if verify_missing:
                            logger.warning(f"After migration, some tables are still missing: {verify_missing}")
                            # Create missing tables as fallback (for fresh databases)
                            logger.info("Creating missing tables using SQLAlchemy metadata...")
                            try:
                                Base.metadata.create_all(bind=sync_engine, checkfirst=True)
                                logger.info("Missing tables created successfully")
                            except Exception as create_exc:
                                logger.error(f"Failed to create missing tables: {create_exc}")
                        else:
                            logger.info("Schema verification passed - all required tables exist")
                else:
                    logger.info("Skipping migrations - database is already compliant")
                    # Even if migrations are skipped, ensure all tables exist
                    with sync_engine.connect() as check_conn:
                        check_inspector = sqlalchemy_inspect(check_conn)
                        check_tables = set(check_inspector.get_table_names())
                        check_missing = required_tables - check_tables
                        
                        if check_missing:
                            logger.info(f"Creating missing tables: {check_missing}")
                            try:
                                Base.metadata.create_all(bind=sync_engine, checkfirst=True)
                                logger.info("Missing tables created successfully")
                            except Exception as create_exc:
                                logger.error(f"Failed to create missing tables: {create_exc}")
            
            sync_engine.dispose()
        else:
            logger.warning("alembic.ini not found - skipping migrations")
    except Exception as migration_exc:
        # If migrations fail, log but don't crash - might be first run or migration issues
        logger.warning(f"Migration check failed (this may be normal on first run): {migration_exc}")
        import traceback
        logger.debug(traceback.format_exc())
    
    # ----- 1.2 Ensure admin user exists (pure async ORM) ----- #
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        logger.warning(
            "Admin credentials not configured - skipping admin user creation."
        )
    else:
        async for db in get_db():  # yields AsyncSession
            try:
                # 1. Check if admin already exists
                result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
                admin = result.scalar_one_or_none()
                
                if admin:
                    logger.info(f"Admin user already exists: {ADMIN_EMAIL}")
                else:
                    admin = User(
                        name=ADMIN_NAME or "Admin",
                        email=ADMIN_EMAIL,
                        hashed_password=hash_password(ADMIN_PASSWORD),
                        is_active=True,
                        is_approved=True,
                        role="admin",
                    )
                    db.add(admin)
                    await db.commit()
                    await db.refresh(admin)  # optional – get generated id
                    logger.info(f"Created admin user: {ADMIN_EMAIL}")
            except OperationalError as exc:  # DB not reachable
                logger.error(f"Database unavailable while handling admin user: {exc}")
                # Do NOT raise – we still want the app to start
            except Exception as exc:  # pragma: no cover
                logger.error(f"Unexpected error handling admin user: {exc}")
            finally:
                # Ensure the session is closed even if something went wrong
                await db.close()
            break  # only one iteration needed
    
    # --------------------------------------------------------------------- #
    # 2. YIELD – Application is running
    # --------------------------------------------------------------------- #
    try:
        yield
    finally:
        # ----------------------------------------------------------------- #
        # 3. SHUTDOWN
        # ----------------------------------------------------------------- #
        logger.info("Application shutting down - disposing DB connections...")
        await engine_async.dispose()


app = FastAPI(
    title="PDF Extraction Tool",
    description="A tool for extracting text from PDFs using multiple AI extraction engines",
    version="1.0.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
# Configure CORS to work with credentials from the frontend origin
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"]
)

# Include auth router in the API router (will be at /api/auth)
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Include PDF routes (no prefix, at root of /api)
app.include_router(pdf.router, tags=["PDF"])

# Include audio routes at /api/audio
app.include_router(audio.router, prefix="/audio", tags=["Audio"])

# Include image routes at /api/image
app.include_router(image.router, prefix="/image", tags=["Image"])

# Expose uploaded files only in development for convenience
if STAGE == "development":
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# --- Image proxy for private assets (S3, etc.) ---
ALLOWED_IMAGE_HOSTS = {
    "pdf-workbench-data-dev.s3.ap-south-1.amazonaws.com",
    # Regional path-style endpoint
    "s3.ap-south-1.amazonaws.com",
    # Legacy global S3 style
    "pdf-workbench-data-dev.s3.amazonaws.com",
}

logger.info("Application Startup Done - Ready to accept requests.............")

@app.get("/proxy/image")
async def proxy_image(url: str = Query(...)):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
        raise HTTPException(status_code=400, detail="Invalid image host")
    
    # Try to fetch using httpx first (for public URLs)
    try:
        # Configure httpx client with redirect following and longer timeout
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            verify=True  # SSL verification
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Return the image with appropriate content type
            content_type = response.headers.get("content-type", "image/jpeg")
            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*",
                }
            )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout proxying image from {url}: {e}")
        raise HTTPException(status_code=504, detail="Timeout while fetching image")
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error proxying image from {url}: {e.response.status_code}. Trying S3 direct access...")
        # Fall through to try S3 direct access
    except httpx.RequestError as e:
        logger.warning(f"Request error proxying image from {url}: {type(e).__name__}. Trying S3 direct access...")
        # Fall through to try S3 direct access
    except Exception as e:
        logger.warning(f"Unexpected httpx error: {type(e).__name__}. Trying S3 direct access...")
        # Fall through to try S3 direct access
    
    # Fallback: Try using boto3 for S3 URLs (handles authentication)
    if "s3" in parsed.hostname.lower() or parsed.hostname.endswith("amazonaws.com"):
        try:
            import aioboto3
            # Extract S3 bucket, region, and key from URL
            # URL format: https://bucket.s3.region.amazonaws.com/key
            # or: https://s3.region.amazonaws.com/bucket/key
            hostname_parts = parsed.hostname.split(".")
            
            # Determine if it's virtual-hosted-style or path-style
            if hostname_parts[0] != "s3" and len(hostname_parts) >= 4:
                # Virtual-hosted-style: bucket.s3.region.amazonaws.com
                bucket_name = hostname_parts[0]
                # Extract region (usually the 3rd part: bucket.s3.REGION.amazonaws.com)
                if len(hostname_parts) >= 3 and hostname_parts[1] == "s3":
                    region_from_url = hostname_parts[2]
                else:
                    region_from_url = AWS_REGION  # Fallback to configured region
                s3_key = parsed.path.lstrip("/")
            else:
                # Path-style: s3.region.amazonaws.com/bucket/key
                path_parts = parsed.path.lstrip("/").split("/", 1)
                if len(path_parts) >= 2:
                    bucket_name, s3_key = path_parts[0], "/".join(path_parts[1:])
                else:
                    bucket_name = path_parts[0] if path_parts else None
                    s3_key = ""
                # Extract region from hostname: s3.REGION.amazonaws.com
                if len(hostname_parts) >= 2:
                    region_from_url = hostname_parts[1]
                else:
                    region_from_url = AWS_REGION
            
            # Use region from URL if available, otherwise fall back to configured region
            s3_region = region_from_url if region_from_url else AWS_REGION
            
            if not bucket_name or not s3_key:
                raise ValueError(f"Could not parse bucket or key from URL: {url}")
            
            logger.info(f"Attempting S3 direct access: bucket={bucket_name}, key={s3_key}, region={s3_region}")
            
            session = aioboto3.Session()
            async with session.client("s3", region_name=s3_region) as s3:
                response = await s3.get_object(Bucket=bucket_name, Key=s3_key)
                file_content = await response["Body"].read()
                content_type = response.get("ContentType", "image/jpeg")
                
                from fastapi.responses import Response
                return Response(
                    content=file_content,
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
        except Exception as s3_error:
            logger.error(f"Failed to fetch from S3: {type(s3_error).__name__} - {str(s3_error)}")
            import traceback
            logger.error(traceback.format_exc())
            # If S3 fails, try one more time with httpx but with no SSL verification as last resort
            # (Some S3 buckets might have SSL issues)
            try:
                logger.info(f"Retrying with httpx (no SSL verification) as last resort...")
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    follow_redirects=True,
                    verify=False  # Disable SSL verification as last resort
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "image/jpeg")
                    from fastapi.responses import Response
                    return Response(
                        content=response.content,
                        media_type=content_type,
                        headers={
                            "Cache-Control": "public, max-age=3600",
                            "Access-Control-Allow-Origin": "*",
                        }
                    )
            except Exception as final_error:
                logger.error(f"Final retry also failed: {type(final_error).__name__} - {str(final_error)}")
                raise HTTPException(
                    status_code=502, 
                    detail=f"Failed to fetch image: {str(s3_error)}"
                )
    
    # If we get here, both methods failed
    logger.error(f"All methods failed for image URL: {url}")
    raise HTTPException(status_code=502, detail="Failed to fetch image")


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {"status": "ok", "message": "PDF Extraction Tool API is running"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
