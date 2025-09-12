"""
Модель для работы с досками Kaiten.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    from .column import Column
    from .card import Card


class Board(KaitenObject):
    """
    Класс для работы с досками Kaiten.
    
    Предоставляет методы для управления доской и получения её колонок и карточек.
    """
    
    @property
    def title(self) -> Optional[str]:
        """Название доски."""
        return self._data.get('title')
    
    @property
    def description(self) -> Optional[str]:
        """Описание доски."""
        return self._data.get('description')
    
    @property
    def board_type(self) -> Optional[str]:
        """Тип доски (kanban, scrum)."""
        return self._data.get('board_type')
    
    @property
    def space_id(self) -> Optional[int]:
        """ID пространства, к которому принадлежит доска."""
        return self._data.get('space_id')
    
    @property
    def created_at(self) -> Optional[str]:
        """Дата создания доски."""
        return self._data.get('created_at')
    
    @property
    def updated_at(self) -> Optional[str]:
        """Дата последнего обновления доски."""
        return self._data.get('updated_at')
    
    async def refresh(self) -> 'Board':
        """Обновить данные доски из API."""
        data = await self._client.get_board(self.id)
        self._data = data
        return self
    
    async def update(self, **fields) -> 'Board':
        """
        Обновить доску.
        
        Args:
            **fields: Поля для обновления (title, description и т.д.)
        
        Returns:
            Обновленная доска
        """
        data = await self._client.update_board(self.space_id, self.id, **fields)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить доску.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_board(self.space_id, self.id)
    
    async def get_columns(self) -> List['Column']:
        """
        Получить все колонки доски.
        
        Returns:
            Список объектов Column
        """
        from .column import Column
        
        columns_data = await self._client.get_columns(self.id)
        return [Column(self._client, column_data) for column_data in columns_data]
    
    async def create_column(
        self,
        title: str,
        position: Optional[int] = None
    ) -> 'Column':
        """
        Создать новую колонку в доске.
        
        Args:
            title: Название колонки
            position: Позиция колонки
        
        Returns:
            Созданная колонка
        """
        from .column import Column
        
        column_data = await self._client.create_column(
            title=title,
            board_id=self.id,
            position=position
        )
        return Column(self._client, column_data)
    
    async def get_cards(self, **filters) -> List['Card']:
        """
        Получить карточки доски.
        
        Args:
            **filters: Фильтры (assignee_id, state, priority и т.д.)
        
        Returns:
            Список объектов Card
        """
        from .card import Card
        
        cards_data = await self._client.get_cards(board_id=self.id, **filters)
        return [Card(self._client, card_data) for card_data in cards_data]
    
    async def create_card(
        self,
        title: str,
        column_id: int,
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
        Создать новую карточку в доске.
        
        Args:
            title: Название карточки
            column_id: ID колонки
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
        from .card import Card
        
        card_data = await self._client.create_card(
            title=title,
            column_id=column_id,
            board_id=self.id,
            description=description,
            assignee_id=assignee_id,
            owner_id=owner_id,
            priority=priority,
            due_date=due_date,
            tags=tags,
            parent_id=parent_id,
            **kwargs
        )
        return Card(self._client, card_data)
    
    def __str__(self) -> str:
        """Строковое представление доски."""
        return f"Board(id={self.id}, title='{self.title}')"
