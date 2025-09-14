"""
Модель для работы с досками Kaiten.
"""

from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    from .column import Column
    from .lane import Lane
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
    def created(self) -> Optional[str]:
        """Дата создания."""
        return self._data.get('created')
    
    @property
    def updated(self) -> Optional[str]:
        """Дата последнего обновления (timestamp)."""
        return self._data.get('updated')
    
    @property
    def cell_wip_limits(self) -> Optional[List[Dict[str, Any]]]:
        """JSON содержащий правила wip лимитов для ячеек."""
        return self._data.get('cell_wip_limits')
    
    @property
    def external_id(self) -> Optional[str]:
        """Внешний идентификатор."""
        return self._data.get('external_id')
    
    @property
    def default_card_type_id(self) -> Optional[int]:
        """Тип карточки по умолчанию для новых карточек на доске."""
        return self._data.get('default_card_type_id')
    
    @property
    def email_key(self) -> Optional[str]:
        """Email ключ."""
        return self._data.get('email_key')
    
    @property
    def move_parents_to_done(self) -> Optional[bool]:
        """Автоматически перемещать родительские карточки в выполненные, когда их дочерние карточки на этой доске выполнены."""
        return self._data.get('move_parents_to_done')
    
    @property
    def default_tags(self) -> Optional[str]:
        """Теги по умолчанию."""
        return self._data.get('default_tags')
    
    @property
    def first_image_is_cover(self) -> Optional[bool]:
        """Автоматически отмечать первое загруженное изображение карточки как обложку карточки."""
        return self._data.get('first_image_is_cover')
    
    @property
    def reset_lane_spent_time(self) -> Optional[bool]:
        """Сбрасывать время, проведенное в дорожке, когда карточка изменила дорожку."""
        return self._data.get('reset_lane_spent_time')
    
    @property
    def backward_moves_enabled(self) -> Optional[bool]:
        """Разрешить автоматическое обратное перемещение для сводных досок."""
        return self._data.get('backward_moves_enabled')
    
    @property
    def hide_done_policies(self) -> Optional[bool]:
        """Скрывать выполненные политики чек-листа."""
        return self._data.get('hide_done_policies')
    
    @property
    def hide_done_policies_in_done_column(self) -> Optional[bool]:
        """Скрывать выполненные политики чек-листа только в колонке выполненных."""
        return self._data.get('hide_done_policies_in_done_column')
    
    @property
    def automove_cards(self) -> Optional[bool]:
        """Автоматически перемещать карточки в зависимости от состояния их дочерних элементов."""
        return self._data.get('automove_cards')
    
    @property
    def auto_assign_enabled(self) -> Optional[bool]:
        """Автоматически назначать пользователя на карточку, когда он/она перемещает карточку, если пользователь не является участником карточки."""
        return self._data.get('auto_assign_enabled')
    
    @property
    def card_properties(self) -> Optional[List[Dict[str, Any]]]:
        """Свойства карточек доски, предлагаемые для заполнения."""
        return self._data.get('card_properties')
    
    @property
    def columns(self) -> Optional[List[Dict[str, Any]]]:
        """Колонки доски."""
        return self._data.get('columns')
    
    @property
    def lanes(self) -> Optional[List[Dict[str, Any]]]:
        """Дорожки доски."""
        return self._data.get('lanes')
    
    @property
    def top(self) -> Optional[int]:
        """Y координата доски в пространстве."""
        return self._data.get('top')
    
    @property
    def left(self) -> Optional[int]:
        """X координата доски в пространстве."""
        return self._data.get('left')
    
    @property
    def sort_order(self) -> Optional[float]:
        """Позиция."""
        return self._data.get('sort_order')
    
    # Оставляем для обратной совместимости
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
        return await self._client.get_columns(self.id)
    
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
        return await self._client.create_column(
            title=title,
            board_id=self.id,
            position=position
        )
    
    async def get_lanes(self) -> List['Lane']:
        """
        Получить все дорожки доски.
        
        Returns:
            Список объектов Lane
        """
        return await self._client.get_lanes(self.id)
    
    async def create_lane(
        self,
        title: str,
        sort_order: Optional[float] = None,
        row_count: Optional[int] = None,
        wip_limit: Optional[int] = None,
        **kwargs
    ) -> 'Lane':
        """
        Создать новую дорожку в доске.
        
        Args:
            title: Название дорожки
            sort_order: Позиция
            row_count: Высота
            wip_limit: Рекомендуемый лимит
            **kwargs: Дополнительные поля
        
        Returns:
            Созданная дорожка
        """
        return await self._client.create_lane(
            title=title,
            board_id=self.id,
            sort_order=sort_order,
            row_count=row_count,
            wip_limit=wip_limit,
            **kwargs
        )
    
    async def get_cards(self, **filters) -> List['Card']:
        """
        Получить карточки доски с расширенными фильтрами.
        
        Args:
            **filters: Любые фильтры поддерживаемые API (created_before, created_after, 
                      updated_before, updated_after, query, tag, states, archived и т.д.)
        
        Returns:
            Список объектов Card
        """
        return await self._client.get_cards(board_id=self.id, **filters)
    
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
        return await self._client.create_card(
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
    
    def __str__(self) -> str:
        """Строковое представление доски."""
        return f"Board(id={self.id}, title='{self.title}')"
