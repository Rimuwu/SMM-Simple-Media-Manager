"""
Модель для работы с пространствами Kaiten.
"""

from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
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
    def uid(self) -> Optional[str]:
        """Уникальный идентификатор пространства."""
        return self._data.get('uid')
    
    @property
    def title(self) -> Optional[str]:
        """Название пространства."""
        return self._data.get('title')
    
    @property
    def description(self) -> Optional[str]:
        """Описание пространства."""
        return self._data.get('description')
    
    @property
    def updated(self) -> Optional[str]:
        """Дата последнего обновления (timestamp)."""
        return self._data.get('updated')
    
    @property
    def created(self) -> Optional[str]:
        """Дата создания."""
        return self._data.get('created')
    
    @property
    def created_at(self) -> Optional[str]:
        """Дата создания пространства."""
        return self._data.get('created_at')
    
    @property
    def updated_at(self) -> Optional[str]:
        """Дата последнего обновления пространства."""
        return self._data.get('updated_at')
    
    @property
    def archived(self) -> Optional[bool]:
        """Флаг архивации пространства."""
        return self._data.get('archived')
    
    @property
    def access(self) -> Optional[str]:
        """Уровень доступа к пространству."""
        return self._data.get('access')
    
    @property
    def for_everyone_access_role_id(self) -> Optional[str]:
        """ID роли для всеобщего доступа."""
        return self._data.get('for_everyone_access_role_id')
    
    @property
    def entity_type(self) -> Optional[str]:
        """Тип сущности."""
        return self._data.get('entity_type')
    
    @property
    def path(self) -> Optional[str]:
        """Внутренний путь к сущности."""
        return self._data.get('path')
    
    @property
    def sort_order(self) -> Optional[float]:
        """Порядок сортировки пространства."""
        return self._data.get('sort_order')
    
    @property
    def parent_entity_uid(self) -> Optional[str]:
        """UID родительской сущности."""
        return self._data.get('parent_entity_uid')
    
    @property
    def company_id(self) -> Optional[int]:
        """ID компании."""
        return self._data.get('company_id')
    
    @property
    def allowed_card_type_ids(self) -> Optional[List[int]]:
        """Список разрешенных типов карточек для этого пространства."""
        return self._data.get('allowed_card_type_ids')
    
    @property
    def external_id(self) -> Optional[str]:
        """Внешний идентификатор."""
        return self._data.get('external_id')
    
    @property
    def settings(self) -> Optional[Dict[str, Any]]:
        """Настройки пространства."""
        return self._data.get('settings')
    
    @property
    def users(self) -> Optional[List[Dict[str, Any]]]:
        """Пользователи пространства."""
        return self._data.get('users')
    
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
        return await self._client.get_boards(self.id)
    
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
        return await self._client.create_board(
            title=title,
            space_id=self.id,
            description=description,
            board_type=board_type
        )
    
    def __str__(self) -> str:
        """Строковое представление пространства."""
        return f"Space(id={self.id}, name='{self.name}')"
