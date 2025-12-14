from datetime import datetime, timedelta
import enum
from typing import Literal, Optional
from uuid import UUID as _UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.connection import session_factory
from global_modules.classes.enums import CardType, ChangeType, UserRole
from global_modules.timezone import now_naive as moscow_now
from modules.kaiten import add_kaiten_comment, get_kaiten_user_name, kaiten
from modules.properties import multi_properties
from global_modules.json_get import open_settings, open_properties, open_clients
from models.Card import Card, CardStatus
from models.User import User
from modules.calendar import create_calendar_event, delete_calendar_event, update_calendar_event
from modules.scheduler import reschedule_post_tasks, schedule_card_notifications, cancel_card_tasks, reschedule_card_notifications, schedule_post_tasks, update_post_tasks_time
from modules.constants import (
    KaitenBoardNames, PropertyNames, 
    SceneNames, Messages
)
from modules.card_service import (
    notify_executor, increment_reviewers_tasks, increment_customer_tasks
)
from modules.executors_client import (
    send_forum_message, update_forum_message, delete_forum_message, delete_forum_message_by_id,
    send_complete_preview, update_complete_preview, delete_complete_preview, delete_all_complete_previews,
    close_user_scene, update_task_scenes, close_card_related_scenes,
    notify_user, notify_users
)
from modules.logs import brain_logger as logger
from modules import status_changers
from modules import card_events

from modules.settings import vk_executor
from modules.settings import all_settings
from modules.settings import tg_executor


router = APIRouter(prefix='/time')


@router.get('/busy-slots')
async def get_busy_slots(start: Optional[str] = None, end: Optional[str] = None):
    """
    Возвращает список занятых слотов (всех `send_time` у карточек).
    Можно опционально фильтровать по диапазону дат (`start` и `end` в ISO формате).
    """
    try:
        start_dt = datetime.fromisoformat(start) if start else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'start' datetime format. Use ISO format.")

    try:
        end_dt = datetime.fromisoformat(end) if end else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'end' datetime format. Use ISO format.")

    async with session_factory() as session:
        try:
            stmt = select(Card.card_id, Card.send_time).where(Card.send_time != None)
            if start_dt:
                stmt = stmt.where(Card.send_time >= start_dt)
            if end_dt:
                stmt = stmt.where(Card.send_time <= end_dt)

            result = await session.execute(stmt)
            rows = result.all()

            slots = []
            for card_id, send_time in rows:
                if not send_time:
                    continue
                slots.append({
                    'card_id': str(card_id),
                    'send_time': send_time.isoformat()
                })

            return {'busy_slots': slots}
        except Exception as e:
            logger.error(f"Error fetching busy slots: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
