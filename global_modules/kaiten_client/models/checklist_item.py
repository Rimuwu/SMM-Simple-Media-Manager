"""
Модель элемента чек-листа карточки для Kaiten API.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime, date

from .base import KaitenObject

if TYPE_CHECKING:
    from ..kaiten_client import KaitenClient


class ChecklistItem(KaitenObject):
    """
    Модель элемента чек-листа карточки в Kaiten.
    
    Элемент чек-листа представляет отдельную задачу в рамках чек-листа,
    которую можно отмечать как выполненную, назначать ответственного и устанавливать срок.
    """

    @property
    def id(self) -> Optional[int]:
        """ID элемента чек-листа."""
        return self._data.get('id')
    
    @property
    def text(self) -> Optional[str]:
        """Текст элемента чек-листа."""
        return self._data.get('text')
    
    @property
    def sort_order(self) -> Optional[float]:
        """Позиция элемента в чек-листе."""
        return self._data.get('sort_order')
    
    @property
    def checked(self) -> Optional[bool]:
        """Флаг, указывающий отмечен ли элемент как выполненный."""
        return self._data.get('checked')
    
    @property
    def checker_id(self) -> Optional[int]:
        """ID пользователя, который отметил элемент."""
        return self._data.get('checker_id')
    
    @property
    def user_id(self) -> Optional[int]:
        """ID текущего пользователя."""
        return self._data.get('user_id')
    
    @property
    def checked_at(self) -> Optional[str]:
        """Дата и время отметки элемента."""
        return self._data.get('checked_at')
    
    @property
    def responsible_id(self) -> Optional[int]:
        """ID пользователя, ответственного за выполнение элемента."""
        return self._data.get('responsible_id')
    
    @property
    def deleted(self) -> Optional[bool]:
        """Флаг, указывающий что элемент удален."""
        return self._data.get('deleted')
    
    @property
    def due_date(self) -> Optional[str]:
        """Срок выполнения элемента в формате YYYY-MM-DD."""
        return self._data.get('due_date')
    
    @property
    def created(self) -> Optional[str]:
        """Дата создания элемента."""
        return self._data.get('created')
    
    @property
    def updated(self) -> Optional[str]:
        """Дата последнего обновления элемента."""
        return self._data.get('updated')
    
    @property
    def card_id(self) -> Optional[int]:
        """ID карточки, к которой принадлежит чек-лист."""
        return self._data.get('card_id')
    
    @property
    def checklist_id(self) -> Optional[int]:
        """ID чек-листа, к которому принадлежит элемент."""
        return self._data.get('checklist_id')
    
    # === МЕТОДЫ УПРАВЛЕНИЯ ЭЛЕМЕНТОМ ===
    
    async def update(
        self,
        text: Optional[str] = None,
        sort_order: Optional[float] = None,
        checklist_id: Optional[int] = None,
        checked: Optional[bool] = None,
        due_date: Optional[str] = None,
        responsible_id: Optional[int] = None,
        remove_responsible: bool = False
    ) -> 'ChecklistItem':
        """
        Обновляет элемент чек-листа.
        
        Args:
            text: Новый текст элемента
            sort_order: Новая позиция элемента
            checklist_id: ID нового чек-листа для перемещения элемента
            checked: Новое состояние элемента (отмечен/не отмечен)
            due_date: Новый срок выполнения в формате YYYY-MM-DD
            responsible_id: ID нового ответственного пользователя
            remove_responsible: Удалить ответственного пользователя
        
        Returns:
            Обновленный объект элемента чек-листа
        """
        if not self.id or not self.card_id or not self.checklist_id:
            raise ValueError("ID элемента, ID карточки и ID чек-листа должны быть установлены")
        
        # Обработка удаления ответственного
        if remove_responsible:
            responsible_id = None
        
        updated_item = await self._client.update_checklist_item(
            card_id=self.card_id,
            checklist_id=self.checklist_id,
            item_id=self.id,
            text=text,
            sort_order=sort_order,
            checklist_id_new=checklist_id,
            checked=checked,
            due_date=due_date,
            responsible_id=responsible_id
        )
        self._data = updated_item._data
        return self
    
    async def delete(self) -> bool:
        """
        Удаляет элемент чек-листа.
        
        Returns:
            True если удаление прошло успешно
        """
        if not self.id or not self.card_id or not self.checklist_id:
            raise ValueError("ID элемента, ID карточки и ID чек-листа должны быть установлены")
        
        return await self._client.delete_checklist_item(
            card_id=self.card_id,
            checklist_id=self.checklist_id,
            item_id=self.id
        )
    
    async def toggle_checked(self) -> 'ChecklistItem':
        """
        Переключает состояние элемента (отмечен/не отмечен).
        
        Returns:
            Обновленный объект элемента
        """
        new_checked = not (self.checked or False)
        return await self.update(checked=new_checked)
    
    async def set_responsible(self, user_id: int) -> 'ChecklistItem':
        """
        Назначает ответственного за выполнение элемента.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Обновленный объект элемента
        """
        return await self.update(responsible_id=user_id)
    
    async def remove_responsible(self) -> 'ChecklistItem':
        """
        Удаляет ответственного за выполнение элемента.
        
        Returns:
            Обновленный объект элемента
        """
        return await self.update(remove_responsible=True)
    
    async def set_due_date(self, due_date: str) -> 'ChecklistItem':
        """
        Устанавливает срок выполнения элемента.
        
        Args:
            due_date: Срок выполнения в формате YYYY-MM-DD
        
        Returns:
            Обновленный объект элемента
        """
        # Проверка формата даты
        try:
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Дата должна быть в формате YYYY-MM-DD")
        
        return await self.update(due_date=due_date)
    
    async def clear_due_date(self) -> 'ChecklistItem':
        """
        Удаляет срок выполнения элемента.
        
        Returns:
            Обновленный объект элемента
        """
        return await self.update(due_date=None)
    
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    
    def is_overdue(self) -> bool:
        """
        Проверяет, просрочен ли элемент.
        
        Returns:
            True если элемент просрочен (не выполнен и срок прошел)
        """
        if not self.due_date or self.checked:
            return False
        
        try:
            due_date_obj = datetime.strptime(self.due_date, '%Y-%m-%d').date()
            return due_date_obj < date.today()
        except ValueError:
            return False
    
    def days_until_due(self) -> Optional[int]:
        """
        Возвращает количество дней до срока выполнения.
        
        Returns:
            Количество дней (отрицательное значение для просроченных)
            или None если срок не установлен
        """
        if not self.due_date:
            return None
        
        try:
            due_date_obj = datetime.strptime(self.due_date, '%Y-%m-%d').date()
            delta = due_date_obj - date.today()
            return delta.days
        except ValueError:
            return None
    
    def get_status_text(self) -> str:
        """
        Возвращает текстовое описание статуса элемента.
        
        Returns:
            Строка с описанием статуса
        """
        if self.checked:
            return "Выполнено"
        elif self.is_overdue():
            return "Просрочено"
        elif self.due_date:
            days = self.days_until_due()
            if days == 0:
                return "Срок сегодня"
            elif days and days > 0:
                return f"Осталось {days} дн."
            else:
                return "К выполнению"
        else:
            return "К выполнению"
    
    def __str__(self) -> str:
        """Строковое представление элемента чек-листа."""
        status = "✓" if self.checked else "○"
        return f"{status} {self.text}"
    
    def __repr__(self) -> str:
        """Подробное строковое представление элемента чек-листа."""
        return (f"ChecklistItem(id={self.id}, text='{self.text}', checked={self.checked}, "
                f"due_date='{self.due_date}', responsible_id={self.responsible_id})")