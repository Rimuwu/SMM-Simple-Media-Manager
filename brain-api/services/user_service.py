from typing import Optional
from sqlalchemy import select

from models.User import User, UserRole
from database.connection import session_factory


class UserService:
    """Сервис для работы с пользователями"""

    @staticmethod
    async def get_user_by_telegram_id(
        telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.telegram_id == telegram_id
                )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.user_id == user_id
                )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_tasker_id(
        tasker_id: str) -> Optional[User]:
        """Получить пользователя по tasker_id"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.tasker_id == tasker_id
                )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_users_by_role(
        role: UserRole) -> list[User]:
        """Получить всех пользователей с определенной ролью"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.role == role
                )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def create_user(
        telegram_id: int,
        role: UserRole = UserRole.copywriter,
        tasker_id: Optional[str] = None
    ) -> User:
        """Создать нового пользователя"""
        async with session_factory() as session:
            user = User(
                telegram_id=telegram_id,
                role=role,
                tasker_id=tasker_id
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    @staticmethod
    async def update_user_role(
        user_id: str, new_role: UserRole) -> Optional[User]:
        """Обновить роль пользователя"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.user_id == user_id
                )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.role = new_role
                await session.commit()
                await session.refresh(user)
            
            return user

    @staticmethod
    async def update_tasker_id(
        user_id: str, tasker_id: str) -> Optional[User]:
        """Обновить tasker_id пользователя"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.user_id == user_id
                )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.tasker_id = tasker_id
                await session.commit()
                await session.refresh(user)
            
            return user

    @staticmethod
    async def delete_user(
        user_id: str) -> bool:
        """Удалить пользователя"""
        async with session_factory() as session:
            stmt = select(User).where(
                User.user_id == user_id
                )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                await session.delete(user)
                await session.commit()
                return True
            
            return False

    @staticmethod
    async def user_exists(
        telegram_id: int,
        tasker_id: str | None = None
        ) -> bool:
        """Проверить существование пользователя по telegram_id"""
        user_by_tg = await UserService.get_user_by_telegram_id(telegram_id)

        if tasker_id:
            user_by_tasker = await UserService.get_user_by_tasker_id(tasker_id)
        else:
            user_by_tasker = None

        user = user_by_tg or user_by_tasker
        return user is not None

    @staticmethod
    async def get_all_users() -> list[User]:
        """Получить всех пользователей"""
        async with session_factory() as session:
            stmt = select(User)
            result = await session.execute(stmt)
            return list(result.scalars().all())
