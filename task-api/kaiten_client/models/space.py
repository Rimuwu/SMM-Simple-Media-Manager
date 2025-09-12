"""
Модель для работы с пространствами Kaiten.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    from .board import Board


class Space(KaitenObject):
    """
    Класс для работы с пространствами Kaiten.
    
    Предоставляет методы для управления пространством и получения его досок.
    """
    
    @property
    def name(self) -> Optional[str]:
        """Название пространства."""
        return self._data.get('name')
    
    @property
    def description(self) -> Optional[str]:
        """Описание пространства."""
        return self._data.get('description')
    
    @property
    def created_at(self) -> Optional[str]:
        """Дата создания пространства."""
        return self._data.get('created_at')
    
    @property
    def updated_at(self) -> Optional[str]:
        """Дата последнего обновления пространства."""
        return self._data.get('updated_at')
    
    async def refresh(self) -> 'Space':
        """Обновить данные пространства из API."""
        data = await self._client.get_space(self.id)
        self._data = data
        return self
    
    async def update(self, **fields) -> 'Space':
        """
        Обновить пространство.
        
        Args:
            **fields: Поля для обновления (name, description и т.д.)
        
        Returns:
            Обновленное пространство
        """
        data = await self._client.update_space(self.id, **fields)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить пространство.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_space(self.id)
    
    async def get_boards(self) -> List['Board']:
        """
        Получить все доски в пространстве.
        
        Returns:
            Список объектов Board
        """
        from .board import Board
        
        boards_data = await self._client.get_boards(self.id)
        return [Board(self._client, board_data) for board_data in boards_data]
    
    async def create_board(
        self,
        title: str,
        description: Optional[str] = None,
        board_type: str = "kanban"
    ) -> 'Board':
        """
        Создать новую доску в пространстве.
        
        Args:
            title: Название доски
            description: Описание доски
            board_type: Тип доски (kanban, scrum)
        
        Returns:
            Созданная доска
        """
        from .board import Board
        
        board_data = await self._client.create_board(
            title=title,
            space_id=self.id,
            description=description,
            board_type=board_type
        )
        return Board(self._client, board_data)
    
    def __str__(self) -> str:
        """Строковое представление пространства."""
        return f"Space(id={self.id}, name='{self.name}')"
