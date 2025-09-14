"""
Модель для работы с тегами Kaiten.
"""

from typing import Optional
from .base import KaitenObject


class Tag(KaitenObject):
    """
    Класс для работы с тегами Kaiten.
    """
    
    @property
    def name(self) -> Optional[str]:
        """Название тега."""
        return self._data.get('name')
    
    @property
    def color(self) -> Optional[str]:
        """Цвет тега (hex формат)."""
        return self._data.get('color')
    
    @property
    def space_id(self) -> Optional[int]:
        """ID пространства, к которому принадлежит тег."""
        return self._data.get('space_id')
    
    async def refresh(self) -> 'Tag':
        """Обновить данные тега из API."""
        data = await self._client.get_tag(self.id)
        self._data = data
        return self
    
    async def update(self, **fields) -> 'Tag':
        """
        Обновить тег.
        
        Args:
            **fields: Поля для обновления (name, color)
        
        Returns:
            Обновленный тег
        """
        data = await self._client.update_tag(self.id, **fields)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить тег.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_tag(self.id)
    
    def __str__(self) -> str:
        """Строковое представление тега."""
        return f"Tag(id={self.id}, name='{self.name}')"
