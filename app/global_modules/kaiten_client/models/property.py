"""
Модель для работы с пользовательскими свойствами (custom properties) Kaiten.
"""

from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from .base import KaitenObject

if TYPE_CHECKING:
    pass


class Property(KaitenObject):
    """
    Класс для работы с пользовательскими свойствами Kaiten.
    
    Предоставляет методы для управления пользовательскими свойствами.
    """
    
    @property
    def name(self) -> Optional[str]:
        """Название пользовательского свойства."""
        return self._data.get('name')
    
    @property
    def type(self) -> Optional[str]:
        """Тип пользовательского свойства."""
        return self._data.get('type')
    
    @property
    def show_on_facade(self) -> Optional[bool]:
        """Показывать ли свойство на фасаде карточки."""
        return self._data.get('show_on_facade')
    
    @property
    def multiline(self) -> Optional[bool]:
        """Отображать ли многострочное текстовое поле."""
        return self._data.get('multiline')
    
    @property
    def vote_variant(self) -> Optional[str]:
        """Тип голосования или коллективного голосования."""
        return self._data.get('vote_variant')
    
    @property
    def values_type(self) -> Optional[str]:
        """Тип значений."""
        return self._data.get('values_type')
    
    @property
    def colorful(self) -> Optional[bool]:
        """Для select свойств. Определяет, должен ли select выбирать цвет при создании нового значения."""
        return self._data.get('colorful')
    
    @property
    def multi_select(self) -> Optional[bool]:
        """Для select свойств. Определяет, используется ли select как мульти-выбор."""
        return self._data.get('multi_select')
    
    @property
    def values_creatable_by_users(self) -> Optional[bool]:
        """Для select свойств. Определяет, могут ли пользователи с ролью writer создавать новые значения."""
        return self._data.get('values_creatable_by_users')
    
    @property
    def data(self) -> Optional[Dict[str, Any]]:
        """Дополнительные данные пользовательского свойства."""
        return self._data.get('data')
    
    @property
    def formula(self) -> Optional[str]:
        """Формула для расчета."""
        return self._data.get('formula')
    
    @property
    def formula_source_card(self) -> Optional[Dict[str, Any]]:
        """Данные карточки, из которых используются для расчета формулы."""
        return self._data.get('formula_source_card')
    
    @property
    def color(self) -> Optional[int]:
        """Цвет catalog пользовательского свойства."""
        return self._data.get('color')
    
    @property
    def fields_settings(self) -> Optional[Dict[str, Any]]:
        """Настройки полей для типа catalog."""
        return self._data.get('fields_settings')
    
    @property
    def author_id(self) -> Optional[int]:
        """ID автора."""
        return self._data.get('author_id')
    
    @property
    def company_id(self) -> Optional[int]:
        """ID компании."""
        return self._data.get('company_id')
    
    @property
    def updated(self) -> Optional[str]:
        """Дата последнего обновления (timestamp)."""
        return self._data.get('updated')
    
    @property
    def created(self) -> Optional[str]:
        """Дата создания."""
        return self._data.get('created')
    
    @property
    def condition(self) -> Optional[str]:
        """Состояние пользовательского свойства."""
        return self._data.get('condition')
    
    @property
    def protected(self) -> Optional[bool]:
        """Флаг защищенности."""
        return self._data.get('protected')
    
    @property
    def external_id(self) -> Optional[str]:
        """Внешний идентификатор."""
        return self._data.get('external_id')
    
    async def refresh(self) -> 'Property':
        """Обновить данные свойства из API."""
        data = await self._client.get_property(self.id)
        self._data = data._data
        return self
    
    async def update(self, **fields) -> 'Property':
        """
        Обновить пользовательское свойство.
        
        Args:
            **fields: Поля для обновления (name, type, show_on_facade и т.д.)
        
        Returns:
            Обновленное свойство
        """
        return await self._client.update_property(self.id, **fields)
    
    async def delete(self) -> bool:
        """
        Удалить пользовательское свойство.
        
        Returns:
            True если удаление прошло успешно
        """
        return await self._client.delete_property(self.id)
    
    def __str__(self) -> str:
        """Строковое представление пользовательского свойства."""
        return f"Property(id={self.id}, name='{self.name}', type='{self.type}')"