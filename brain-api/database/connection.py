from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from os import getenv

engine = create_async_engine(
    getenv("DATABASE_URL", ''), 
    future=True, 
    echo=getenv("DEBUG", 'False').lower() == 'true',
    #  pool_size=5, 
    #  max_overflow=10
    )

session_factory = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    )

Base = declarative_base()
