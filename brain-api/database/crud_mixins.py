from sqlalchemy import select, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from database.connection import session_factory

class AsyncCRUDMixin:
    """Миксин для асинхронных CRUD операций без явной передачи сессии"""

    @asynccontextmanager
    async def _get_session(self, session: Optional[AsyncSession] = None):
        """Контекстный менеджер для получения сессии"""
        if session:
            # Если сессия передана, используем её без закрытия
            yield session
        else:
            # Создаем новую сессию и закрываем её
            async with session_factory() as new_session:
                try:
                    yield new_session
                finally:
                    await new_session.close()
    
    async def save(self, session: Optional[AsyncSession] = None):
        """Сохраняет текущий объект в БД"""
        async with self._get_session(session) as sess:
            sess.add(self)
            if not session:  # Коммитим только если сессия наша
                await sess.commit()
            return self
    
    async def update(self, session: Optional[AsyncSession] = None, **kwargs):
        """Обновляет поля объекта"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        async with self._get_session(session) as sess:
            if hasattr(self, '__table__'):
                # Используем merge для обновления
                merged_obj = await sess.merge(self)
                if not session:  # Коммитим только если сессия наша
                    await sess.commit()
                
                # Обновляем текущий объект значениями из merged_obj
                for column in self.__table__.columns:  # type: ignore
                    setattr(self, column.name, getattr(merged_obj, column.name))
                
                return self
            else:
                return self

    async def refresh(self, session: Optional[AsyncSession] = None):
        """Обновляет объект данными из базы"""
        async with self._get_session(session) as sess:
            if hasattr(self, '__table__'):
                pk_column = list(self.__table__.primary_key.columns)[0]  # type: ignore
                pk_value = getattr(self, pk_column.name)
                
                # Получаем свежие данные из БД
                result = await sess.execute(
                    select(self.__class__).where(pk_column == pk_value)
                )
                fresh_obj = result.scalar_one_or_none()
                
                if fresh_obj:
                    # Обновляем текущий объект свежими данными
                    for column in self.__table__.columns:  # type: ignore
                        setattr(self, column.name, getattr(fresh_obj, column.name))
                    return self
                else:
                    raise ValueError(f"Object with {pk_column.name}={pk_value} not found in database")
            else:
                raise ValueError(f"Object don't have a table associated")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        result = {}
        if hasattr(self, '__table__'):
            for column in self.__table__.columns:  # type: ignore
                value = getattr(self, column.name)
                if hasattr(value, '__str__') and 'UUID' in str(type(value)):
                    result[column.name] = str(value)
                else:
                    result[column.name] = value
        return result

    @classmethod
    async def create(cls, session: Optional[AsyncSession] = None, **kwargs):
        """Создает новый объект и сохраняет в БД"""
        obj = cls(**kwargs)
        
        if session:
            session.add(obj)
            # Не коммитим, если сессия внешняя
            try:
                await session.refresh(obj)
            except:
                pass  # refresh может не сработать до коммита
            return obj
        else:
            async with session_factory() as sess:
                sess.add(obj)
                await sess.commit()
                try:
                    await sess.refresh(obj)
                except:
                    pass
                return obj

    @classmethod
    async def get_by_id(cls, id_value: Any, session: Optional[AsyncSession] = None):
        """Получает объект по первичному ключу"""
        async with cls._get_session_static(session) as sess:
            if hasattr(cls, '__table__'):
                pk_column = list(cls.__table__.primary_key.columns)[0]  # type: ignore
                result = await sess.execute(
                    select(cls).where(pk_column == id_value)
                )
                return result.scalar_one_or_none()
            return None

    @classmethod
    async def get_by_key(cls, key: str, value: Any, session: Optional[AsyncSession] = None):
        """Получает объект по указанному полю"""
        async with cls._get_session_static(session) as sess:
            if hasattr(cls, key):
                result = await sess.execute(
                    select(cls).where(getattr(cls, key) == value)
                )
                return result.scalar_one_or_none()
            return None

    async def delete(self, session: Optional[AsyncSession] = None) -> None:
        """Удаляет объект из БД"""
        async with self._get_session(session) as sess:
            if hasattr(self, '__table__'):
                pk_column = list(self.__table__.primary_key.columns)[0]  # type: ignore
                pk_value = getattr(self, pk_column.name)
                await sess.execute(
                    sql_delete(self.__class__).where(pk_column == pk_value)
                )
                if not session:  # Коммитим только если сессия наша
                    await sess.commit()

    @classmethod
    @asynccontextmanager
    async def _get_session_static(cls, session: Optional[AsyncSession] = None):
        """Статический метод для получения сессии в классовых методах"""
        if session:
            yield session
        else:
            async with session_factory() as new_session:
                try:
                    yield new_session
                finally:
                    await new_session.close()

    @classmethod
    async def get_all(cls, limit: Optional[int] = None, session: Optional[AsyncSession] = None):
        """Получает все объекты"""
        async with cls._get_session_static(session) as sess:
            query = select(cls)
            if limit:
                query = query.limit(limit)
            result = await sess.execute(query)
            return list(result.scalars().all())

    @classmethod
    async def filter_by(cls, session: Optional[AsyncSession] = None, **kwargs):
        """Фильтрует объекты по указанным полям"""
        async with cls._get_session_static(session) as sess:
            query = select(cls)
            for key, value in kwargs.items():
                if hasattr(cls, key):
                    query = query.where(getattr(cls, key) == value)
            result = await sess.execute(query)
            return list(result.scalars().all())

    @classmethod
    async def first_or_create(cls, defaults: Optional[Dict] = None, session: Optional[AsyncSession] = None, **kwargs):
        """Получает объект или создает новый если не найден"""
        async with cls._get_session_static(session) as sess:
            query = select(cls)
            for key, value in kwargs.items():
                if hasattr(cls, key):
                    query = query.where(getattr(cls, key) == value)
            
            result = await sess.execute(query)
            obj = result.scalar_one_or_none()
            
            if obj:
                return obj, False
            else:
                create_kwargs = kwargs.copy()
                if defaults:
                    create_kwargs.update(defaults)
                obj = await cls.create(session=sess, **create_kwargs)
                return obj, True

    @classmethod
    async def all(cls, session: Optional[AsyncSession] = None):
        """Получает все объекты (алиас для get_all)"""
        return await cls.get_all(session=session)