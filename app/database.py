import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

# ---------------------------
# Database URL
# ---------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set in the .env file")

# ---------------------------
# Engine
# ---------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # set True for SQL debug logs
    future=True
)

# ---------------------------
# Session Local
# ---------------------------
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------
# Base model
# ---------------------------
Base = declarative_base()

# ---------------------------
# Dependency for FastAPI
# ---------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
