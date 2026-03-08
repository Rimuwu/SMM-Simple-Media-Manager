

from database.connection import Base, engine, session_factory
from sqlalchemy import select, text
import logging
from os import getenv

# Отключаем логирование SQL параметров
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

from models import User
from models.Tag import Tag
from models.Card import Card
from models.CardContent import CardContent
from models.CardEditorNote import CardEditorNote
from models.ClientSetting import ClientSetting
from models.Entity import Entity
from models.CardFile import CardFile
from models.CardMessage import CardMessage

from modules.enums import UserRole

async def create_tables():
    """Удалить все таблицы и пересоздать их заново."""

    async with engine.begin() as conn:
        # Удаляем все таблицы с CASCADE для обхода зависимостей
        # await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(
            text("CREATE SCHEMA IF NOT EXISTS public")
            )
        await conn.run_sync(Base.metadata.create_all)

async def create_superuser():
    """Создать суперпользователя, если его нет в базе."""

    admin_id = getenv("ADMIN_ID", None)
    if not admin_id:
        print("ADMIN_ID not set, skipping superuser creation.")
        return

    async with session_factory() as session:
        stmt = select(User).where(
                User.telegram_id == int(admin_id)
            )
        result = await session.execute(stmt)
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("Superuser already exists.")
            return

        new_admin = User(
            telegram_id=int(admin_id),
            role=UserRole.admin,
            department='smm',
            about="Superuser"
        )
        session.add(new_admin)
        await session.commit()
        print("Superuser created.")