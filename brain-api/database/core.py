


from config import Settings
from database.connection import Base, engine
from sqlalchemy import text
import models

async def create_tables():
    """Удалить все таблицы и пересоздать их заново."""

    engine.echo = False
    async with engine.begin() as conn:
        # Удаляем все таблицы с CASCADE для обхода зависимостей
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        # Создаём заново
        await conn.run_sync(Base.metadata.create_all)
    engine.echo = getattr(Settings, "debug", False)