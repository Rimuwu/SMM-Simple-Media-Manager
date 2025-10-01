"""
Модель для работы с комментариями Kaiten.
"""

from typing import Optional
from .base import KaitenObject


class Comment(KaitenObject):
    """
    Класс для работы с комментариями карточек Kaiten.
    """
    
    @property
    def text(self) -> Optional[str]:
        """Текст комментария."""
        return self._data.get('text')
    
    @property
    def card_id(self) -> Optional[int]:
        """ID карточки, к которой принадлежит комментарий."""
        return self._data.get('card_id')
    
    @property
    def author_id(self) -> Optional[int]:
        """ID автора комментария."""
        return self._data.get('author_id')
    
    @property
    def created_at(self) -> Optional[str]:
        """Дата создания комментария."""
        return self._data.get('created_at')
    
    @property
    def updated_at(self) -> Optional[str]:
        """Дата последнего обновления комментария."""
        return self._data.get('updated_at')
    
    async def refresh(self) -> 'Comment':
        """Обновить данные комментария из API."""
        # Для комментариев нет отдельного эндпоинта получения по ID
        # Нужно получить все комментарии карточки и найти нужный
        comments_data = await self._client.get_card_comments(self.card_id)
        for comment_data in comments_data:
            if comment_data.get('id') == self.id:
                self._data = comment_data
                break
        return self
    
    async def update(self, text: str) -> 'Comment':
        """
        Обновить комментарий.
        
        Args:
            text: Новый текст комментария
        
        Returns:
            Обновленный комментарий
        """
        data = await self._client.update_comment(self.card_id, self.id, text)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить комментарий.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_comment(self.card_id, self.id)
    
    def __str__(self) -> str:
        """Строковое представление комментария."""
        text_preview = self.text[:50] + "..." if self.text and len(self.text) > 50 else self.text
        return f"Comment(id={self.id}, text='{text_preview}')"
