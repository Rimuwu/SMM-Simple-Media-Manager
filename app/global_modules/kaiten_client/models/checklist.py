"""
Модель чек-листа карточки для Kaiten API.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

from .base import KaitenObject

if TYPE_CHECKING:
    from ..kaiten_client import KaitenClient
    from .checklist_item import ChecklistItem


class Checklist(KaitenObject):
    """
    Модель чек-листа карточки в Kaiten.
    
    Чек-лист содержит упорядоченный список элементов (ChecklistItem),
    которые можно отмечать как выполненные, назначать ответственных и устанавливать сроки.
    """

    @property
    def id(self) -> Optional[int]:
        """ID чек-листа."""
        return self._data.get('id')
    
    @property
    def name(self) -> Optional[str]:
        """Название чек-листа."""
        return self._data.get('name')
    
    @property
    def created(self) -> Optional[str]:
        """Дата создания чек-листа."""
        return self._data.get('created')
    
    @property
    def updated(self) -> Optional[str]:
        """Дата последнего обновления чек-листа."""
        return self._data.get('updated')
    
    @property
    def sort_order(self) -> Optional[float]:
        """Позиция чек-листа среди других чек-листов карточки."""
        return self._data.get('sort_order')
    
    @property
    def policy_id(self) -> Optional[int]:
        """ID шаблона чек-листа (если создан из шаблона)."""
        return self._data.get('policy_id')
    
    @property
    def checklist_id(self) -> Optional[str]:
        """Строковый ID чек-листа карточки."""
        return self._data.get('checklist_id')
    
    @property
    def deleted(self) -> Optional[bool]:
        """Флаг, указывающий что чек-лист удален."""
        return self._data.get('deleted')
    
    @property
    def card_id(self) -> Optional[int]:
        """ID карточки, к которой принадлежит чек-лист."""
        return self._data.get('card_id')
    
    @property
    def items(self) -> Optional[List[Dict[str, Any]]]:
        """Список элементов чек-листа."""
        return self._data.get('items', [])
    
    # === МЕТОДЫ УПРАВЛЕНИЯ ЧЕКИСТОМ ===
    
    async def refresh(self) -> 'Checklist':
        """
        Обновляет данные чек-листа с сервера.
        
        Returns:
            Обновленный объект чек-листа
        """
        if not self.id or not self.card_id:
            raise ValueError("ID чек-листа и ID карточки должны быть установлены")
        
        updated_checklist = await self._client.get_checklist(self.card_id, self.id)
        self._data = updated_checklist._data
        return self
    
    async def update(
        self,
        name: Optional[str] = None,
        sort_order: Optional[float] = None,
        card_id: Optional[int] = None
    ) -> 'Checklist':
        """
        Обновляет чек-лист.
        
        Args:
            name: Новое название чек-листа
            sort_order: Новая позиция чек-листа
            card_id: ID карточки для перемещения чек-листа
        
        Returns:
            Обновленный объект чек-листа
        """
        if not self.id or not self.card_id:
            raise ValueError("ID чек-листа и ID карточки должны быть установлены")
        
        updated_checklist = await self._client.update_checklist(
            card_id=self.card_id,
            checklist_id=self.id,
            name=name,
            sort_order=sort_order,
            move_to_card_id=card_id
        )
        self._data = updated_checklist._data
        return self
    
    async def delete(self) -> bool:
        """
        Удаляет чек-лист.
        
        Returns:
            True если удаление прошло успешно
        """
        if not self.id or not self.card_id:
            raise ValueError("ID чек-листа и ID карточки должны быть установлены")
        
        return await self._client.delete_checklist(self.card_id, self.id)
    
    # === МЕТОДЫ УПРАВЛЕНИЯ ЭЛЕМЕНТАМИ ===
    
    async def add_item(
        self,
        text: str,
        sort_order: Optional[float] = None,
        checked: Optional[bool] = None,
        due_date: Optional[str] = None,
        responsible_id: Optional[int] = None
    ) -> 'ChecklistItem':
        """
        Добавляет новый элемент в чек-лист.
        
        Args:
            text: Текст элемента
            sort_order: Позиция элемента
            checked: Состояние элемента (отмечен/не отмечен)
            due_date: Срок выполнения в формате YYYY-MM-DD
            responsible_id: ID ответственного пользователя
        
        Returns:
            Созданный элемент чек-листа
        """
        if not self.id or not self.card_id:
            raise ValueError("ID чек-листа и ID карточки должны быть установлены")
        
        return await self._client.add_checklist_item(
            card_id=self.card_id,
            checklist_id=self.id,
            text=text,
            sort_order=sort_order,
            checked=checked,
            due_date=due_date,
            responsible_id=responsible_id
        )
    
    async def get_items(self) -> List['ChecklistItem']:
        """
        Получает все элементы чек-листа как объекты ChecklistItem.
        
        Returns:
            Список элементов чек-листа
        """
        from .checklist_item import ChecklistItem
        
        items_data = self.items or []
        result = []
        
        for item_data in items_data:
            # Добавляем контекстную информацию
            item_data['card_id'] = self.card_id
            item_data['checklist_id'] = self.id
            result.append(ChecklistItem(self._client, item_data))
        
        return result
    
    # === СТАТИСТИЧЕСКИЕ МЕТОДЫ ===
    
    def get_completion_stats(self) -> Dict[str, Any]:
        """
        Получает статистику выполнения чек-листа.
        
        Returns:
            Словарь со статистикой (total, completed, percentage)
        """
        items = self.items or []
        total = len(items)
        completed = sum(1 for item in items if item.get('checked', False))
        percentage = (completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'percentage': round(percentage, 2)
        }
    
    def is_completed(self) -> bool:
        """
        Проверяет, завершен ли чек-лист полностью.
        
        Returns:
            True если все элементы отмечены как выполненные
        """
        items = self.items or []
        return len(items) > 0 and all(item.get('checked', False) for item in items)
    
    def get_overdue_items(self) -> List[Dict[str, Any]]:
        """
        Получает список просроченных элементов чек-листа.
        
        Returns:
            Список просроченных элементов
        """
        from datetime import date
        
        today = date.today()
        overdue_items = []
        
        for item in self.items or []:
            due_date_str = item.get('due_date')
            if due_date_str and not item.get('checked', False):
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    if due_date < today:
                        overdue_items.append(item)
                except ValueError:
                    # Некорректный формат даты
                    continue
        
        return overdue_items
    
    def __str__(self) -> str:
        """Строковое представление чек-листа."""
        stats = self.get_completion_stats()
        return f"Checklist(id={self.id}, name='{self.name}', completion={stats['completed']}/{stats['total']})"
    
    def __repr__(self) -> str:
        """Подробное строковое представление чек-листа."""
        return (f"Checklist(id={self.id}, name='{self.name}', card_id={self.card_id}, "
                f"items_count={len(self.items or [])}, created='{self.created}')")