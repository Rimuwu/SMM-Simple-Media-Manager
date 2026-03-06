"""
Базовый класс для всех объектов Kaiten API.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from ..kaiten_client import KaitenClient


class KaitenObject:
    """
    Базовый класс для всех объектов Kaiten.
    
    Предоставляет общие методы и свойства для работы с данными из API.
    """
    
    def __init__(self, client: 'KaitenClient', data: Dict[str, Any]):
        """
        Инициализация объекта.
        
        Args:
            client: Экземпляр KaitenClient для выполнения API запросов
            data: Данные объекта из API
        """
        self._client = client
        self._data = data
        self._id = data.get('id')
    
    @property
    def id(self) -> Optional[int]:
        """ID объекта."""
        return self._id
    
    @property
    def data(self) -> Dict[str, Any]:
        """Сырые данные объекта."""
        return self._data.copy()
    
    def __getitem__(self, key: str) -> Any:
        """Доступ к данным через квадратные скобки."""
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        """Проверка наличия ключа в данных."""
        return key in self._data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения с возможностью указать значение по умолчанию."""
        return self._data.get(key, default)
    
    def __str__(self) -> str:
        """Строковое представление объекта."""
        return f"{self.__class__.__name__}(id={self.id})"
    
    def __repr__(self) -> str:
        """Подробное строковое представление объекта."""
        return f"{self.__class__.__name__}(id={self.id}, data={self._data})"
    
    def __eq__(self, other) -> bool:
        """Сравнение объектов по ID."""
        if not isinstance(other, KaitenObject):
            return False
        return self.id == other.id and self.__class__ == other.__class__
    
    def __hash__(self) -> int:
        """Хэш объекта на основе ID и типа."""
        return hash((self.__class__, self.id))
    
    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        """Парсинг даты из строки ISO формата."""
        if not value:
            return None
        try:
            # Kaiten использует ISO формат с Z в конце
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    
    def refresh(self):
        """
        Обновить данные объекта из API.
        
        Метод должен быть переопределен в наследниках для конкретных эндпоинтов.
        """
        raise NotImplementedError("Subclasses must implement refresh method")
    
    def update(self, **fields) -> 'KaitenObject':
        """
        Обновить объект.
        
        Метод должен быть переопределен в наследниках для конкретных эндпоинтов.
        """
        raise NotImplementedError("Subclasses must implement update method")
    
    def delete(self) -> bool:
        """
        Удалить объект.
        
        Метод должен быть переопределен в наследниках для конкретных эндпоинтов.
        """
        raise NotImplementedError("Subclasses must implement delete method")
