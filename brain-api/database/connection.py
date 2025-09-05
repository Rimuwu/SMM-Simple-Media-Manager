from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings
engine = create_async_engine(
    settings.database_url, 
    future=True, 
    echo=getattr(settings, "debug", False),
    #  pool_size=5, 
    #  max_overflow=10
    )
session_factory = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    )

Base = declarative_base()
