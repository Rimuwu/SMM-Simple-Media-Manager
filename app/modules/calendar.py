"""
Модуль для работы с Google Calendar.

В монолите заменяет HTTP-вызовы к calendar-api прямыми вызовами calendar_manager.
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from modules.logs import brain_logger as logger

# Ленивая инициализация - calendar_manager создаётся только если Google Calendar настроен
_calendar_manager = None


def _get_manager():
    global _calendar_manager
    if _calendar_manager is None:
        try:
            from modules.calendar_manager import GoogleCalendarManager
            _calendar_manager = GoogleCalendarManager()
        except Exception as e:
            logger.warning(f"Google Calendar не инициализирован: {e}")
            _calendar_manager = False
    return _calendar_manager if _calendar_manager else None


async def _run_sync(func, *args, **kwargs):
    """Запустить синхронную функцию Google Calendar в thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def create_calendar_event(
    title: str,
    description: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    all_day: bool = False,
    attendees: Optional[List[str]] = None,
    location: str = "",
    color_id: Optional[str] = None
) -> Dict[str, Any]:
    """Создание нового события в календаре."""
    if attendees is None:
        attendees = []

    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    logger.info(f"Создание события в календаре: {title}, Начало: {start_time}")
    try:
        event = await _run_sync(
            manager.create_event,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            attendees=attendees,
            location=location,
            color_id=color_id
        )
        return {"response": event, "status": 200 if event else 500}
    except Exception as e:
        logger.error(f"Ошибка создания события в календаре: {e}")
        return {"response": None, "status": 500}


async def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Обновление существующего события в календаре."""
    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if start_time is not None:
        update_data["start_time"] = start_time
    if end_time is not None:
        update_data["end_time"] = end_time
    if location is not None:
        update_data["location"] = location
    if attendees is not None:
        update_data["attendees"] = attendees

    logger.info(f"Обновление события в календаре {event_id}: {list(update_data.keys())}")
    try:
        event = await _run_sync(manager.update_event, event_id=event_id, **update_data)
        return {"response": event, "status": 200 if event else 500}
    except Exception as e:
        logger.error(f"Ошибка обновления события в календаре {event_id}: {e}")
        return {"response": None, "status": 500}


async def get_calendar_events(
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 10,
    order_by: str = "startTime"
) -> Dict[str, Any]:
    """Получение списка событий из календаря."""
    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    try:
        events = await _run_sync(
            manager.get_events,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            order_by=order_by
        )
        return {"response": events, "status": 200}
    except Exception as e:
        logger.error(f"Ошибка получения событий из календаря: {e}")
        return {"response": None, "status": 500}


async def get_calendar_event(event_id: str) -> Dict[str, Any]:
    """Получение конкретного события по ID."""
    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    try:
        event = await _run_sync(manager.get_event, event_id=event_id)
        return {"response": event, "status": 200 if event else 404}
    except Exception as e:
        logger.error(f"Ошибка получения события {event_id}: {e}")
        return {"response": None, "status": 500}


async def delete_calendar_event(event_id: str) -> Dict[str, Any]:
    """Удаление события из календаря."""
    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    logger.info(f"Удаление события из календаря: {event_id}")
    try:
        result = await _run_sync(manager.delete_event, event_id=event_id)
        return {"response": result, "status": 200}
    except Exception as e:
        logger.error(f"Ошибка удаления события из календаря {event_id}: {e}")
        return {"response": None, "status": 500}


async def check_calendar_availability(
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """Проверка доступности времени в календаре."""
    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    try:
        result = await _run_sync(
            manager.check_availability,
            start_time=start_time,
            end_time=end_time
        )
        return {"response": result, "status": 200}
    except Exception as e:
        logger.error(f"Ошибка проверки доступности в календаре: {e}")
        return {"response": None, "status": 500}


async def get_today_events() -> Dict[str, Any]:
    """Получение событий на сегодня."""
    manager = _get_manager()
    if not manager:
        return {"response": None, "status": 503}

    try:
        events = await _run_sync(manager.get_today_events)
        return {"response": events, "status": 200}
    except Exception as e:
        logger.error(f"Ошибка получения событий на сегодня: {e}")
        return {"response": None, "status": 500}
