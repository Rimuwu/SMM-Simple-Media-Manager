


from config import Settings
from database.connection import Base, engine

async def create_tables():
    """Удалить все таблицы и пересоздать их заново."""

    engine.echo = False
    async with engine.begin() as conn:
        # Удаляем все таблицы
        await conn.run_sync(Base.metadata.drop_all)
        # Создаём заново
        await conn.run_sync(Base.metadata.create_all)
    engine.echo = getattr(Settings, "debug", False)