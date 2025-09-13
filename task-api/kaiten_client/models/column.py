"""
Модель для работы с колонками Kaiten.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    from .card import Card


class Column(KaitenObject):
    """
    Класс для работы с колонками Kaiten.
    
    Предоставляет методы для управления колонкой и получения её карточек.
    """
    
    @property
    def title(self) -> Optional[str]:
        """Название колонки."""
        return self._data.get('title')
    
    @property
    def board_id(self) -> Optional[int]:
        """ID доски, к которой принадлежит колонка."""
        return self._data.get('board_id')
    
    @property
    def position(self) -> Optional[int]:
        """Позиция колонки на доске."""
        return self._data.get('position')
    
    @property
    def created_at(self) -> Optional[str]:
        """Дата создания колонки."""
        return self._data.get('created_at')
    
    @property
    def updated_at(self) -> Optional[str]:
        """Дата последнего обновления колонки."""
        return self._data.get('updated_at')
    
    async def refresh(self) -> 'Column':
        """Обновить данные колонки из API."""
        data = await self._client.get_column(self.board_id, self.id)
        self._data = data
        return self
    
    async def update(self, **fields) -> 'Column':
        """
        Обновить колонку.
        
        Args:
            **fields: Поля для обновления (title, position и т.д.)
        
        Returns:
            Обновленная колонка
        """
        data = await self._client.update_column(self.board_id, self.id, **fields)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить колонку.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_column(self.board_id, self.id)
    
    async def get_cards(self, **filters) -> List['Card']:
        """
        Получить все карточки в колонке с расширенными фильтрами.
        
        Args:
            **filters: Любые фильтры поддерживаемые API (created_before, created_after, 
                      updated_before, updated_after, query, tag, states, archived и т.д.)
        
        Returns:
            Список объектов Card в этой колонке
        """
        from .card import Card
        
        # Используем фильтр column_id напрямую в API для более эффективного запроса
        return await self._client.get_cards(board_id=self.board_id, column_id=self.id, **filters)
    
    async def create_card(
        self,
        title: str,
        description: Optional[str] = None,
        assignee_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        tags: Optional[List[int]] = None,
        parent_id: Optional[int] = None,
        **kwargs
    ) -> 'Card':
        """
        Создать новую карточку в колонке.
        
        Args:
            title: Название карточки
            description: Описание карточки
            assignee_id: ID исполнителя
            owner_id: ID владельца
            priority: Приоритет (low, normal, high, critical)
            due_date: Срок выполнения (ISO формат)
            tags: Список ID тегов
            parent_id: ID родительской карточки
            **kwargs: Дополнительные поля
        
        Returns:
            Созданная карточка
        """
        return await self._client.create_card(
            title=title,
            column_id=self.id,
            board_id=self.board_id,
            description=description,
            assignee_id=assignee_id,
            owner_id=owner_id,
            priority=priority,
            due_date=due_date,
            tags=tags,
            parent_id=parent_id,
            **kwargs
        )
    
    def __str__(self) -> str:
        """Строковое представление колонки."""
        return f"Column(id={self.id}, title='{self.title}')"
