from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from global_modules.vault.vault_client import vault_getenv

POSTGRES_USER = vault_getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = vault_getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = vault_getenv("POSTGRES_DB", "database")

engine = create_async_engine(
    f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}', 
    future=True, 
    echo=vault_getenv("DEBUG", 'False').lower() == 'true',
    #  pool_size=5, 
    #  max_overflow=10
    )

session_factory = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    )

Base = declarative_base()
