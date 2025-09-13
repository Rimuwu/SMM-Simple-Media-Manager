"""
Модель для работы с карточками Kaiten.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    from .comment import Comment
    from .member import Member
    from .file import File
    from .checklist import Checklist


class Card(KaitenObject):
    """
    Класс для работы с карточками Kaiten.
    
    Предоставляет методы для управления карточкой и работы с её компонентами
    (комментарии, файлы, участники).
    """
    
    @property
    def title(self) -> Optional[str]:
        """Название карточки."""
        return self._data.get('title')
    
    @property
    def description(self) -> Optional[str]:
        """Описание карточки."""
        return self._data.get('description')
    
    @property
    def column_id(self) -> Optional[int]:
        """ID колонки, в которой находится карточка."""
        return self._data.get('column_id')
    
    @property
    def board_id(self) -> Optional[int]:
        """ID доски, к которой принадлежит карточка."""
        return self._data.get('board_id')
    
    @property
    def assignee_id(self) -> Optional[int]:
        """ID исполнителя карточки."""
        return self._data.get('assignee_id')
    
    @property
    def owner_id(self) -> Optional[int]:
        """ID владельца карточки."""
        return self._data.get('owner_id')
    
    @property
    def priority(self) -> Optional[str]:
        """Приоритет карточки (low, normal, high, critical)."""
        return self._data.get('priority')
    
    @property
    def due_date(self) -> Optional[str]:
        """Срок выполнения карточки."""
        return self._data.get('due_date')
    
    @property
    def tags(self) -> List[int]:
        """Список ID тегов карточки."""
        return self._data.get('tags', [])
    
    @property
    def parent_id(self) -> Optional[int]:
        """ID родительской карточки."""
        return self._data.get('parent_id')
    
    @property
    def created_at(self) -> Optional[str]:
        """Дата создания карточки."""
        return self._data.get('created_at')
    
    @property
    def updated_at(self) -> Optional[str]:
        """Дата последнего обновления карточки."""
        return self._data.get('updated_at')
    
    async def refresh(self) -> 'Card':
        """Обновить данные карточки из API."""
        data = await self._client.get_card(self.id)
        self._data = data
        return self
    
    async def update(self, **fields) -> 'Card':
        """
        Обновить карточку.
        
        Args:
            **fields: Поля для обновления (title, description, column_id и т.д.)
        
        Returns:
            Обновленная карточка
        """
        data = await self._client.update_card(self.id, **fields)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить карточку.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_card(self.id)
    
    async def move_to_column(self, column_id: int) -> 'Card':
        """
        Переместить карточку в другую колонку.
        
        Args:
            column_id: ID целевой колонки
        
        Returns:
            Обновленная карточка
        """
        return await self.update(column_id=column_id)
    
    # === КОММЕНТАРИИ ===
    
    async def get_comments(self) -> List['Comment']:
        """
        Получить все комментарии карточки.
        
        Returns:
            Список объектов Comment
        """
        return await self._client.get_card_comments(self.id)
    
    async def add_comment(self, text: str) -> 'Comment':
        """
        Добавить комментарий к карточке.
        
        Args:
            text: Текст комментария
        
        Returns:
            Созданный комментарий
        """
        return await self._client.add_comment(self.id, text)
    
    # === УЧАСТНИКИ ===
    
    async def get_members(self) -> List['Member']:
        """
        Получить всех участников карточки.
        
        Returns:
            Список объектов Member
        """
        return await self._client.get_card_members(self.id)
    
    async def add_member(self, user_id: int) -> 'Member':
        """
        Добавить участника к карточке.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Добавленный участник
        """
        return await self._client.add_card_member(self.id, user_id)
    
    async def remove_member(self, user_id: int) -> bool:
        """
        Удалить участника из карточки.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.remove_card_member(self.id, user_id)
    
    # === ФАЙЛЫ ===
    
    async def get_files(self) -> List['File']:
        """
        Получить все файлы карточки.
        
        Returns:
            Список объектов File
        """
        return await self._client.get_card_files(self.id)
    
    async def upload_file(self, file_path: str, file_name: Optional[str] = None) -> 'File':
        """
        Загрузить файл к карточке.
        
        Args:
            file_path: Путь к файлу
            file_name: Имя файла (если отличается от file_path)
        
        Returns:
            Информация о загруженном файле
        """
        return await self._client.upload_file(self.id, file_path, file_name)
    
    # === ЧЕКИСТЫ ===
    
    async def get_checklists(self) -> List['Checklist']:
        """
        Получить все чек-листы карточки.
        
        Returns:
            Список чек-листов
        """
        return await self._client.get_card_checklists(self.id)
    
    async def create_checklist(
        self,
        name: str,
        sort_order: Optional[float] = None,
        items_source_checklist_id: Optional[int] = None,
        exclude_item_ids: Optional[List[int]] = None,
        source_share_id: Optional[int] = None
    ) -> 'Checklist':
        """
        Создать новый чек-лист в карточке.
        
        Args:
            name: Название чек-листа
            sort_order: Позиция чек-листа
            items_source_checklist_id: ID чек-листа для копирования элементов
            exclude_item_ids: ID элементов для исключения при копировании
            source_share_id: ID шаблона чек-листа
        
        Returns:
            Созданный чек-лист
        """
        return await self._client.create_checklist(
            card_id=self.id,
            name=name,
            sort_order=sort_order,
            items_source_checklist_id=items_source_checklist_id,
            exclude_item_ids=exclude_item_ids,
            source_share_id=source_share_id
        )
    
    def __str__(self) -> str:
        """Строковое представление карточки."""
        return f"Card(id={self.id}, title='{self.title}')"
