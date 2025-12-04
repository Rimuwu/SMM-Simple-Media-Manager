from .api_client import calendar_api
from typing import Optional, List, Dict, Any
from datetime import datetime
from modules.logs import brain_logger as logger


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
    """
    Создание нового события в календаре
    
    Args:
        title: Название события
        description: Описание события
        start_time: Время начала события
        end_time: Время окончания события
        all_day: Событие на весь день
        attendees: Список email участников
        location: Место проведения
        color_id: ID цвета события (1-11)
    
    Returns:
        Dict с результатом создания события
    """
    if attendees is None:
        attendees = []
    
    event_data = {
        "title": title,
        "description": description,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "all_day": all_day,
        "attendees": attendees,
        "location": location,
        "color_id": color_id
    }
    
    logger.info(f"Создание события в календаре: {title}, Начало: {start_time}")
    response, status = await calendar_api.post("/calendar/events", data=event_data)
    
    if status != 200:
        logger.error(f"Ошибка создания события в календаре: {response}")
        
    return {"response": response, "status": status}


async def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Обновление существующего события в календаре
    
    Args:
        event_id: ID события для обновления
        title: Новое название события
        description: Новое описание события
        start_time: Новое время начала
        end_time: Новое время окончания
        location: Новое место проведения
        attendees: Новый список участников
    
    Returns:
        Dict с результатом обновления события
    """
    update_data = {}
    
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if start_time is not None:
        update_data["start_time"] = start_time.isoformat()
    if end_time is not None:
        update_data["end_time"] = end_time.isoformat()
    if location is not None:
        update_data["location"] = location
    if attendees is not None:
        update_data["attendees"] = attendees
    
    logger.info(f"Обновление события в календаре {event_id}: {update_data}")
    response, status = await calendar_api.put(f"/calendar/events/{event_id}", data=update_data)
    
    if status != 200:
        logger.error(f"Ошибка обновления события в календаре {event_id}: {response}")
        
    return {"response": response, "status": status}


async def get_calendar_events(
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 10,
    order_by: str = "startTime"
) -> Dict[str, Any]:
    """
    Получение списка событий из календаря
    
    Args:
        time_min: Минимальное время для поиска
        time_max: Максимальное время для поиска
        max_results: Максимальное количество результатов (1-100)
        order_by: Сортировка результатов
    
    Returns:
        Dict со списком событий
    """
    params = {
        "max_results": max_results,
        "order_by": order_by
    }
    
    if time_min:
        params["time_min"] = time_min.isoformat()
    if time_max:
        params["time_max"] = time_max.isoformat()
    
    response, status = await calendar_api.get("/calendar/events", params=params, use_cache=True)
    return {"response": response, "status": status}


async def get_calendar_event(event_id: str) -> Dict[str, Any]:
    """
    Получение конкретного события по ID
    
    Args:
        event_id: ID события
    
    Returns:
        Dict с данными события
    """
    response, status = await calendar_api.get(f"/calendar/events/{event_id}", use_cache=True)
    return {"response": response, "status": status}


async def delete_calendar_event(event_id: str) -> Dict[str, Any]:
    """
    Удаление события из календаря
    
    Args:
        event_id: ID события для удаления
    
    Returns:
        Dict с результатом удаления
    """
    logger.info(f"Удаление события из календаря: {event_id}")
    response, status = await calendar_api.delete(f"/calendar/events/{event_id}")
    
    if status != 200:
        logger.error(f"Ошибка удаления события из календаря {event_id}: {response}")
        
    return {"response": response, "status": status}


async def check_calendar_availability(
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """
    Проверка доступности времени в календаре
    
    Args:
        start_time: Время начала проверяемого периода
        end_time: Время окончания проверяемого периода
    
    Returns:
        Dict с результатом проверки доступности
    """
    availability_data = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    response, status = await calendar_api.post("/calendar/availability/check", data=availability_data)
    return {"response": response, "status": status}


async def get_today_events() -> Dict[str, Any]:
    """
    Получение событий на сегодня
    
    Returns:
        Dict со списком событий на сегодня
    """
    response, status = await calendar_api.get("/calendar/events/today", use_cache=True)
    return {"response": response, "status": status}


async def get_week_events() -> Dict[str, Any]:
    """
    Получение событий на текущую неделю
    
    Returns:
        Dict со списком событий на неделю
    """
    response, status = await calendar_api.get("/calendar/events/week", use_cache=True)
    return {"response": response, "status": status}


async def get_calendar_info() -> Dict[str, Any]:
    """
    Получение информации о календаре
    
    Returns:
        Dict с информацией о календаре
    """
    response, status = await calendar_api.get("/calendar/info", use_cache=True)
    return {"response": response, "status": status}


# Дополнительные вспомогательные функции

async def search_events(
    query: str,
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 25
) -> Dict[str, Any]:
    """
    Поиск событий по тексту в названии или описании
    
    Args:
        query: Поисковый запрос
        time_min: Минимальное время для поиска
        time_max: Максимальное время для поиска
        max_results: Максимальное количество результатов
    
    Returns:
        Dict со списком найденных событий
    """
    params = {
        "q": query,
        "max_results": max_results
    }
    
    if time_min:
        params["time_min"] = time_min.isoformat()
    if time_max:
        params["time_max"] = time_max.isoformat()
    
    response, status = await calendar_api.get("/calendar/events", params=params, use_cache=True)
    return {"response": response, "status": status}


async def get_events_by_date_range(
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    Получение событий за указанный диапазон дат
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
    
    Returns:
        Dict со списком событий за период
    """
    return await get_calendar_events(
        time_min=start_date,
        time_max=end_date,
        max_results=100
    )


async def create_recurring_event(
    title: str,
    description: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    recurrence_rule: str = "",
    location: str = "",
    attendees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Создание повторяющегося события
    
    Args:
        title: Название события
        description: Описание события
        start_time: Время начала события
        end_time: Время окончания события
        recurrence_rule: Правило повторения (RRULE)
        location: Место проведения
        attendees: Список участников
    
    Returns:
        Dict с результатом создания события
    """
    if attendees is None:
        attendees = []
    
    event_data = {
        "title": title,
        "description": description,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "location": location,
        "attendees": attendees,
        "recurrence": [recurrence_rule] if recurrence_rule else []
    }
    
    response, status = await calendar_api.post("/calendar/events", data=event_data)
    return {"response": response, "status": status}


async def get_free_busy_info(
    time_min: datetime,
    time_max: datetime,
    calendar_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Получение информации о занятости календаря
    
    Args:
        time_min: Начальное время
        time_max: Конечное время
        calendar_ids: Список ID календарей (если не указан, используется основной)
    
    Returns:
        Dict с информацией о занятости
    """
    if calendar_ids is None:
        calendar_ids = []
    
    busy_data = {
        "time_min": time_min.isoformat(),
        "time_max": time_max.isoformat(),
        "calendar_ids": calendar_ids
    }
    
    response, status = await calendar_api.post("/calendar/freebusy", data=busy_data)
    return {"response": response, "status": status}


def is_event_response_successful(response_data: Dict[str, Any]) -> bool:
    """
    Проверка успешности ответа от календарного API
    
    Args:
        response_data: Ответ от API
    
    Returns:
        True если запрос успешен, False в противном случае
    """
    return (
        response_data.get("status") in [200, 201] and
        response_data.get("response", {}).get("success", False)
    )


def extract_event_data(response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Извлечение данных события из ответа API
    
    Args:
        response_data: Ответ от API
    
    Returns:
        Данные события или None если не найдены
    """
    if is_event_response_successful(response_data):
        return response_data.get("response", {}).get("data")
    return None


def extract_events_list(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Извлечение списка событий из ответа API
    
    Args:
        response_data: Ответ от API
    
    Returns:
        Список событий
    """
    if is_event_response_successful(response_data):
        return response_data.get("response", {}).get("data", [])
    return []