from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    from .card import Card


class Lane(KaitenObject):
    """
    Класс для работы с дорожками Kaiten.
    
    Предоставляет методы для управления дорожкой и получения её карточек.
    """
    
    @property
    def title(self) -> Optional[str]:
        """Название дорожки."""
        return self._data.get('title')
    
    @property
    def updated(self) -> Optional[str]:
        """Дата последнего обновления (timestamp)."""
        return self._data.get('updated')
    
    @property
    def created(self) -> Optional[str]:
        """Дата создания."""
        return self._data.get('created')
    
    @property
    def sort_order(self) -> Optional[float]:
        """Позиция."""
        return self._data.get('sort_order')
    
    @property
    def row_count(self) -> Optional[int]:
        """Высота."""
        return self._data.get('row_count')
    
    @property
    def wip_limit(self) -> Optional[int]:
        """Рекомендуемый лимит для колонки."""
        return self._data.get('wip_limit')
    
    @property
    def board_id(self) -> Optional[int]:
        """ID доски."""
        return self._data.get('board_id')
    
    @property
    def default_card_type_id(self) -> Optional[int]:
        """Тип карточки по умолчанию для новых карточек в дорожке."""
        return self._data.get('default_card_type_id')
    
    @property
    def wip_limit_type(self) -> Optional[int]:
        """Тип WIP лимита (1 – количество карточек, 2 – размер карточек)."""
        return self._data.get('wip_limit_type')
    
    @property
    def external_id(self) -> Optional[str]:
        """Внешний идентификатор."""
        return self._data.get('external_id')
    
    @property
    def default_tags(self) -> Optional[str]:
        """Теги по умолчанию."""
        return self._data.get('default_tags')
    
    @property
    def last_moved_warning_after_days(self) -> Optional[int]:
        """Предупреждение появляется на устаревших карточках (дни)."""
        return self._data.get('last_moved_warning_after_days')
    
    @property
    def last_moved_warning_after_hours(self) -> Optional[int]:
        """Предупреждение появляется на устаревших карточках (часы)."""
        return self._data.get('last_moved_warning_after_hours')
    
    @property
    def last_moved_warning_after_minutes(self) -> Optional[int]:
        """Предупреждение появляется на устаревших карточках (минуты)."""
        return self._data.get('last_moved_warning_after_minutes')
    
    @property
    def condition(self) -> Optional[int]:
        """Состояние (1 - активная, 2 - архивная, 3 - удаленная)."""
        return self._data.get('condition')
    
    async def refresh(self) -> 'Lane':
        """Обновить данные дорожки из API."""
        data = await self._client.get_lane(self.board_id, self.id)
        self._data = data
        return self
    
    async def update(self, **fields) -> 'Lane':
        """
        Обновить дорожку.
        
        Args:
            **fields: Поля для обновления (title, sort_order и т.д.)
        
        Returns:
            Обновленная дорожка
        """
        data = await self._client.update_lane(self.board_id, self.id, **fields)
        self._data = data
        return self
    
    async def delete(self) -> bool:
        """
        Удалить дорожку.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_lane(self.board_id, self.id)
    
    async def get_cards(self, **filters) -> List['Card']:
        """
        Получить все карточки в дорожке с расширенными фильтрами.
        
        Args:
            **filters: Любые фильтры поддерживаемые API (created_before, created_after, 
                      updated_before, updated_after, query, tag, states, archived и т.д.)
        
        Returns:
            Список объектов Card в этой дорожке
        """
        from .card import Card
        
        # Используем фильтр lane_id напрямую в API для более эффективного запроса
        return await self._client.get_cards(board_id=self.board_id, lane_id=self.id, **filters)
    
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
        Создать новую карточку в дорожке.
        
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
            board_id=self.board_id,
            lane_id=self.id,
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
        """Строковое представление дорожки."""
        return f"Lane(id={self.id}, title='{self.title}')"
