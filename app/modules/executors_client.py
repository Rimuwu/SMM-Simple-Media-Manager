"""
Клиент для взаимодействия brain-модулей с executor-ами.

В монолите заменяет HTTP-вызовы к executors-api прямыми вызовами через executor_bridge.
"""
from typing import Optional
from uuid import UUID as _UUID

from modules import executor_bridge
from modules.constants import SceneNames
from modules.logs import logger

from models.Card import Card
from models.CardMessage import CardMessage


# ==================== Форум ====================

async def send_forum_message(card_id: str) -> tuple[int | None, str | None]:
    try:
        result = await executor_bridge.send_forum_message(card_id)
        error = result.get("error")
        if error:
            logger.error(f"Ошибка отправки в форум: {error}")
            return None, error
        message_id = result.get("message_id")
        card = await Card.get_by_id(_UUID(card_id))
        if card and message_id:
            card_message = await card.get_forum_message()
            if not card_message:
                await CardMessage.create(card_id=card.card_id, message_type="forum", message_id=message_id)
            elif card_message.message_id != message_id:
                await card_message.update(message_id=message_id)
        return message_id, None
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в форум: {e}")
        return None, str(e)


async def update_forum_message(card_id: str) -> tuple[int | None, str | None]:
    try:
        result = await executor_bridge.update_forum_message(card_id)
        if result.get("error"):
            return None, result.get("error")
        message_id = result.get("message_id")
        card = await Card.get_by_id(_UUID(card_id))
        if card:
            card_message = await card.get_forum_message()
            if not card_message and message_id:
                await CardMessage.create(card_id=card.card_id, message_type="forum", message_id=message_id)
            elif card_message and card_message.message_id != message_id and message_id:
                await card_message.update(message_id=message_id)
        return message_id, None
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения форума: {e}")
        return None, str(e)


async def delete_forum_message(card_id: str) -> bool:
    try:
        return await executor_bridge.delete_forum_message(card_id)
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения форума: {e}")
        return False


async def delete_forum_message_by_id(message_id: int) -> bool:
    try:
        return await executor_bridge.delete_forum_message_by_id(message_id)
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения форума по ID: {e}")
        return False


async def send_complete_preview(card_id: str, client_key: str, session=None) -> dict:
    try:
        preview_res = await executor_bridge.send_complete_preview(card_id, client_key)
        if preview_res.get("success") is True:
            card = await Card.get_by_id(_UUID(card_id))
            if card:
                post_ids = preview_res.get("post_ids") or []
                info_id = preview_res.get("info_id")
                if session:
                    for pid in post_ids:
                        session.add(CardMessage(card_id=card.card_id, message_type="complete_preview", message_id=pid))
                    if info_id:
                        session.add(CardMessage(card_id=card.card_id, message_type="complete_info", message_id=info_id))
                else:
                    for pid in post_ids:
                        await CardMessage.create(card_id=card.card_id, message_type="complete_preview", message_id=pid)
                    if info_id:
                        await CardMessage.create(card_id=card.card_id, message_type="complete_info", message_id=info_id)
        return preview_res
    except Exception as e:
        logger.error(f"Ошибка отправки complete preview: {e}")
        return {"success": False, "error": str(e)}


async def update_complete_preview(card_id: str, client_key: str, post_ids=None, info_id=None, entities=None) -> dict:
    try:
        return await executor_bridge.update_complete_preview(card_id, client_key, post_ids=post_ids, info_id=info_id, entities=entities)
    except Exception as e:
        logger.error(f"Ошибка обновления complete preview: {e}")
        return {"success": False, "error": str(e)}


async def delete_all_complete_previews(info_ids=None, post_ids=None, entities=None) -> dict:
    try:
        return await executor_bridge.delete_complete_preview(info_ids=info_ids, post_ids=post_ids, entities=entities)
    except Exception as e:
        logger.error(f"Ошибка удаления complete preview: {e}")
        return {"success": False, "error": str(e)}


async def notify_user(user_id: int, message: str) -> bool:
    try:
        return await executor_bridge.notify_user(user_id, message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        return False


async def notify_users(user_ids, message: str, action: str = None) -> None:
    """Send notifications to multiple users. Accepts telegram_id (int) or user_id (UUID)."""
    from global_modules.brain_client import get_user as _get_user
    for uid in user_ids:
        if uid is None:
            continue
        try:
            # UUID — ищем telegram_id
            if isinstance(uid, _UUID) or (isinstance(uid, str) and '-' in str(uid)):
                user = await _get_user(user_id=_UUID(str(uid)))
                if user:
                    telegram_id = user.get('telegram_id')
                    if telegram_id:
                        await notify_user(telegram_id, message)
            else:
                await notify_user(int(uid), message)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя {uid}: {e}")


async def update_task_scenes(card_id: str) -> int:
    return await executor_bridge.update_scenes(scene_name=SceneNames.VIEW_TASK, data_key="task_id", data_value=str(card_id), action="update")


async def close_user_scene(user_id: int) -> int:
    return await executor_bridge.update_scenes(users_id=[user_id], action="close")


async def close_card_related_scenes(card_id: str) -> int:
    return await executor_bridge.update_scenes(data_key="task_id", data_value=str(card_id), action="close")


async def update_scenes(
    scene_name: Optional[str] = None,
    page_name: Optional[str] = None,
    data_key: Optional[str] = None,
    data_value: Optional[str] = None,
    action: str = "update",
    users_id: Optional[list] = None
) -> int:
    return await executor_bridge.update_scenes(
        scene_name=scene_name, page_name=page_name,
        data_key=data_key, data_value=data_value,
        action=action, users_id=users_id
    )


async def delete_complete_preview(
    info_ids: Optional[list] = None,
    post_ids: Optional[list] = None,
    entities: Optional[list] = None
) -> dict:
    return await executor_bridge.delete_complete_preview(
        info_ids=info_ids, post_ids=post_ids, entities=entities
    )
