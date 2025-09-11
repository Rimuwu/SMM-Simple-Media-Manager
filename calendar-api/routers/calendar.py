from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from modules.calendar import calendar_manager
from modules.logs import calendar_logger

router = APIRouter(prefix="/calendar", tags=["calendar"])


# Pydantic модели для запросов и ответов
class EventCreate(BaseModel):
    title: str = Field(..., description="Название события")
    description: str = Field("", description="Описание события")
    start_time: Optional[datetime] = Field(None, description="Время начала события")
    end_time: Optional[datetime] = Field(None, description="Время окончания события")
    all_day: bool = Field(False, description="Событие на весь день")
    attendees: List[str] = Field([], description="Список email участников")
    location: str = Field("", description="Место проведения")
    color_id: Optional[str] = Field(None, description="ID цвета события 1-11")


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Новое название события")
    description: Optional[str] = Field(None, description="Новое описание события")
    start_time: Optional[datetime] = Field(None, description="Новое время начала")
    end_time: Optional[datetime] = Field(None, description="Новое время окончания")
    location: Optional[str] = Field(None, description="Новое место проведения")
    attendees: Optional[List[str]] = Field(None, description="Новый список участников")


class AvailabilityCheck(BaseModel):
    start_time: datetime = Field(..., description="Время начала проверяемого периода")
    end_time: datetime = Field(..., description="Время окончания проверяемого периода")


# Endpoints
@router.get("/info")
async def get_calendar_info():
    """Получение информации о календаре"""
    try:
        calendar_info = calendar_manager.get_calendar_info()
        if not calendar_info:
            raise HTTPException(status_code=500, detail="Не удалось получить информацию о календаре")
        
        return {
            "success": True,
            "data": calendar_info
        }
    except Exception as e:
        calendar_logger.error(f"Error getting calendar info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events")
async def create_event(event_data: EventCreate):
    """Создание нового события в календаре"""
    try:
        created_event = calendar_manager.create_event(
            title=event_data.title,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            all_day=event_data.all_day,
            attendees=event_data.attendees,
            location=event_data.location,
            color_id=event_data.color_id
        )
        
        if not created_event:
            raise HTTPException(status_code=500, detail="Не удалось создать событие")
        
        return {
            "success": True,
            "data": created_event,
            "message": "Событие успешно создано"
        }
    except Exception as e:
        calendar_logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_events(
    time_min: Optional[datetime] = Query(None, description="Минимальное время для поиска"),
    time_max: Optional[datetime] = Query(None, description="Максимальное время для поиска"),
    max_results: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    order_by: str = Query("startTime", description="Сортировка результатов")
):
    """Получение списка событий из календаря"""
    try:
        # Устанавливаем значения по умолчанию, если не переданы
        if not time_min:
            time_min = datetime.now()
        if not time_max:
            time_max = time_min + timedelta(days=30)
        
        events = calendar_manager.get_events(
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            order_by=order_by
        )
        
        return {
            "success": True,
            "data": events,
            "count": len(events)
        }
    except Exception as e:
        calendar_logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Получение конкретного события по ID"""
    try:
        event = calendar_manager.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        return {
            "success": True,
            "data": event
        }
    except HTTPException:
        raise
    except Exception as e:
        calendar_logger.error(f"Error getting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/events/{event_id}")
async def update_event(event_id: str, event_data: EventUpdate):
    """Обновление существующего события"""
    try:
        updated_event = calendar_manager.update_event(
            event_id=event_id,
            title=event_data.title,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            location=event_data.location,
            attendees=event_data.attendees
        )
        
        if not updated_event:
            raise HTTPException(status_code=404, detail="Событие не найдено или не удалось обновить")
        
        return {
            "success": True,
            "data": updated_event,
            "message": "Событие успешно обновлено"
        }
    except HTTPException:
        raise
    except Exception as e:
        calendar_logger.error(f"Error updating event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Удаление события"""
    try:
        success = calendar_manager.delete_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Событие не найдено или не удалось удалить")
        
        return {
            "success": True,
            "message": "Событие успешно удалено"
        }
    except HTTPException:
        raise
    except Exception as e:
        calendar_logger.error(f"Error deleting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/availability/check")
async def check_availability(availability_data: AvailabilityCheck):
    """Проверка доступности времени в календаре"""
    try:
        is_available = calendar_manager.check_availability(
            start_time=availability_data.start_time,
            end_time=availability_data.end_time
        )
        
        return {
            "success": True,
            "available": is_available,
            "period": {
                "start": availability_data.start_time,
                "end": availability_data.end_time
            }
        }
    except Exception as e:
        calendar_logger.error(f"Error checking availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/today")
async def get_today_events():
    """Получение событий на сегодня"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        events = calendar_manager.get_events(
            time_min=today,
            time_max=tomorrow,
            max_results=50
        )
        
        return {
            "success": True,
            "data": events,
            "count": len(events),
            "date": today.strftime("%Y-%m-%d")
        }
    except Exception as e:
        calendar_logger.error(f"Error getting today's events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/week")
async def get_week_events():
    """Получение событий на текущую неделю"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        
        events = calendar_manager.get_events(
            time_min=week_start,
            time_max=week_end,
            max_results=100
        )
        
        return {
            "success": True,
            "data": events,
            "count": len(events),
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d")
        }
    except Exception as e:
        calendar_logger.error(f"Error getting week events: {e}")
        raise HTTPException(status_code=500, detail=str(e))