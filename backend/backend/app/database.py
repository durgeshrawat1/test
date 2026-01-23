from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# 1. Create the Async Engine
# "pool_pre_ping=True" is CRITICAL for Aurora to handle connection drops gracefully
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,           # Adjust based on your Aurora instance size
    max_overflow=10
)

# 2. Create the Session Factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. Base Class for Models
Base = declarative_base()

# 4. Dependency for Routes to get DB Session
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
