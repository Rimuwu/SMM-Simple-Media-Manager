import pprint
from aiogram import Bot
from tg.oms.models.scene import Scene
from tg.main import TelegramExecutor
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal, Optional
from uuid import UUID
from modules.executors_manager import manager
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tg.oms.manager import scene_manager
from modules.logs import executors_logger as logger

router = APIRouter(prefix="/events", tags=["Events"])

class ScenesEvent(BaseModel):
    scene_name: Optional[str] = None
    page_name: Optional[str] = None
    data_key: Optional[str] = None
    data_value: Optional[str] = None
    action: Literal["update", "close"] = "update"
    users_id: Optional[list[int]] = None

@router.post("/update_scenes")
async def update_scenes(event: ScenesEvent):
    """
    Обновляет (перезагружает) все активные сцены, соответствующие указанным критериям.

    Параметры:
    - scene_name: название сцены (например, 'user-task')
    - page_name: название текущей страницы (например, 'main-page')
    - data_key: ключ в данных сцены для проверки (например, 'task_id')
    - data_value: значение для проверки (например, UUID карточки)
    - action: действие - "update" для перезагрузки, "close" для закрытия сцены
    - users_id: список user_id пользователей, чьи сцены нужно обновить

    Пример использования:
    Обновить все сцены редактирования задачи с task_id = "123e4567-e89b-12d3-a456-426614174000"
    """
    active_scenes = list(scene_manager._instances.values())
    updated_count = 0

    users = list(set(event.users_id)) if event.users_id else None

    for scene in active_scenes:
        # Проверяем соответствие критериям
        match = True

        # Проверка названия сцены
        if event.scene_name and scene.__scene_name__ != event.scene_name:
            match = False

        # Проверка текущей страницы
        if event.page_name and scene.current_page.__page_name__ != event.page_name:
            match = False

        # Проверка данных
        if event.data_key and event.data_value:
            scene_value = scene.data.get('scene', {}).get(event.data_key)
            # Приводим к строке для сравнения
            if str(scene_value) != str(event.data_value):
                match = False

        # Проверка user_id
        if users and scene.user_id not in users:
            match = False

        # Если все критерии совпадают - обновляем сцену
        if match:
            try:
                if event.action == "close": 
                    await scene.end()
                    print(f"Получен сигнал остановки сцены для пользователя {scene.user_id}")
                else: await scene.update_message()

                updated_count += 1
            except Exception as e:
                print(f"Failed to update scene for user {scene.user_id}: {e}")
    
    return {
        "status": "ok",
        "total_active_scenes": len(active_scenes),
        "updated_scenes": updated_count
    }


class NotifyUserEvent(BaseModel):
    user_id: int
    message: str
    skip_if_page: Optional[str | list[str]] = None
    reply_to: Optional[int] = None
    parse_mode: Optional[str] = None

@router.post("/notify_user")
async def notify_user(event: NotifyUserEvent):
    """
    Отправляет уведомление пользователю с кнопкой удаления.
    Если указаны task_id и skip_if_page, проверяет, не находится ли пользователь на этой странице.
    """
    logger.info(f"Отправка уведомления пользователю {event.user_id}: {event.message[:50]}...")

    try:
        # Проверяем, нужно ли пропускать уведомление
        if event.skip_if_page:
            active_scenes: list[Scene] = list(
                scene_manager._instances.values())
            pages_to_skip = event.skip_if_page if isinstance(event.skip_if_page, list) else [event.skip_if_page]

            for scene in active_scenes:
                if scene.user_id == event.user_id:
                    if scene.current_page.__page_name__ in pages_to_skip:

                        return {
                            "status": "skipped", 
                            "reason": "User is on the page"
                        }

        client_executor: TelegramExecutor = manager.get(
            "telegram_executor") # type: ignore
        bot: Bot = client_executor.bot
        

        # Создаем клавиатуру с кнопкой удаления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_message")]
        ])

        await bot.send_message(
            chat_id=event.user_id,
            text=event.message,
            reply_markup=keyboard,
            reply_to_message_id=event.reply_to,
            parse_mode=event.parse_mode
        )

        return {"status": "ok", "sent": True}
    except Exception as e:
        print(f"Error sending notification to user {event.user_id}: {e}")
        return {"status": "error", "error": str(e), "sent": False}