"""
Модель для работы с участниками карточек Kaiten.
"""

from typing import Optional
from .base import KaitenObject


class Member(KaitenObject):
    """
    Класс для работы с участниками карточек Kaiten.
    """
    
    @property
    def user_id(self) -> Optional[int]:
        """ID пользователя."""
        return self._data.get('user_id')
    
    @property
    def card_id(self) -> Optional[int]:
        """ID карточки, к которой принадлежит участник."""
        return self._data.get('card_id')
    
    @property
    def name(self) -> Optional[str]:
        """Имя пользователя."""
        return self._data.get('name')
    
    @property
    def email(self) -> Optional[str]:
        """Email пользователя."""
        return self._data.get('email')
    
    @property
    def role(self) -> Optional[str]:
        """Роль участника в карточке."""
        return self._data.get('role')
    
    @property
    def added_at(self) -> Optional[str]:
        """Дата добавления участника к карточке."""
        return self._data.get('added_at')
    
    async def refresh(self) -> 'Member':
        """Обновить данные участника из API."""
        # Для участников нет отдельного эндпоинта получения по ID
        # Нужно получить всех участников карточки и найти нужного
        members_data = await self._client.get_card_members(self.card_id)
        for member_data in members_data:
            if member_data.get('user_id') == self.user_id:
                self._data = member_data
                break
        return self
    
    async def remove(self) -> bool:
        """
        Удалить участника из карточки.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.remove_card_member(self.card_id, self.user_id)
    
    # Участники не имеют отдельного update метода в API
    def update(self, **fields):
        """Участники не поддерживают обновление через API."""
        raise NotImplementedError("Members cannot be updated via API")
    
    def delete(self) -> bool:
        """Удалить участника (алиас для remove)."""
        return self.remove()
    
    def __str__(self) -> str:
        """Строковое представление участника."""
        return f"Member(user_id={self.user_id}, name='{self.name}')"
