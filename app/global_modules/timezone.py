"""
Модуль для работы с московским временем.
Используется везде вместо datetime.now() и datetime.utcnow()
"""

from datetime import datetime, timezone, timedelta

# Московская временная зона (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


def now() -> datetime:
    """
    Получить текущее время в московской временной зоне.
    
    Returns:
        datetime: Текущее время с timezone info (MSK)
    """
    return datetime.now(MOSCOW_TZ)


def now_naive() -> datetime:
    """
    Получить текущее время в московской временной зоне без timezone info.
    Используется для сравнения с naive datetime из базы данных.
    
    Returns:
        datetime: Текущее московское время без timezone info
    """
    return datetime.now(MOSCOW_TZ).replace(tzinfo=None)


def from_timestamp(timestamp: float) -> datetime:
    """
    Преобразовать timestamp в московское время.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        datetime: Время в московской временной зоне
    """
    return datetime.fromtimestamp(timestamp, MOSCOW_TZ)


def to_moscow(dt: datetime) -> datetime:
    """
    Преобразовать datetime в московское время.
    
    Args:
        dt: datetime объект (может быть naive или aware)
        
    Returns:
        datetime: Время в московской временной зоне
    """
    if dt.tzinfo is None:
        # Если naive datetime, предполагаем что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ)
