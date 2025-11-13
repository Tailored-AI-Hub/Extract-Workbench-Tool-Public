from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .constants import ASYNC_DATABASE_URL

engine_async = create_async_engine(ASYNC_DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine_async,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()
        
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session