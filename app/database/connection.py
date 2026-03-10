from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from os import getenv

POSTGRES_USER = getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = getenv("POSTGRES_DB", "database")

engine = create_async_engine(
    f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}', 
    future=True, 
    echo=False
    )

session_factory = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    )

Base = declarative_base()
