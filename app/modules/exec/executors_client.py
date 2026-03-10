"""
Клиент для взаимодействия brain-модулей с executor-ами.
Реализует все операции напрямую, без промежуточного executor_bridge.
"""
from typing import Optional
from uuid import UUID as _UUID

from modules.constants import SceneNames
from modules.logs import logger
from app.models.Message import CardMessage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.card.Card import Card

def _get_tg():
    from modules.exec.executors_manager import manager
    return manager.get("telegram_executor")


# ==================== Форум ====================

async def send_forum_message(card_id: str) -> tuple[int | None, str | None]:
    try:
        from modules.text_generators import forum_message
        result = await forum_message(card_id)
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
        from modules.text_generators import forum_message
        result = await forum_message(card_id)
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
        from modules.text_generators import card_deleted
        result = await card_deleted(card_id)
        return result.get("success", False)
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения форума: {e}")
        return False


async def delete_forum_message_by_id(message_id: int) -> bool:
    try:
        from modules.json_utils import open_settings
        tg = _get_tg()
        if not tg:
            return False
        settings = open_settings() or {}
        group_forum = settings.get("group_forum", 0)
        result = await tg.delete_message(
            chat_id=str(group_forum),
            message_id=str(message_id)
        )
        return result.get("success", False)
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения форума по ID: {e}")
        return False


async def send_complete_preview(card_id: str, client_key: str, session=None) -> dict:
    try:
        from modules.text_generators import send_complete_preview as _send
        preview_res = await _send(card_id, client_key)
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
        from modules.text_generators import update_complete_preview as _update
        return await _update(card_id, client_key, post_ids=post_ids, info_id=info_id, entities=entities)
    except Exception as e:
        logger.error(f"Ошибка обновления complete preview: {e}")
        return {"success": False, "error": str(e)}


async def delete_all_complete_previews(info_ids=None, post_ids=None, entities=None) -> dict:
    try:
        from modules.text_generators import delete_complete_preview as _delete
        return await _delete(info_ids=info_ids, post_ids=post_ids, entities=entities)
    except Exception as e:
        logger.error(f"Ошибка удаления complete preview: {e}")
        return {"success": False, "error": str(e)}


# ==================== Уведомления ====================

async def notify_user(
    telegram_id: int,
    message: str,
    reply_to: Optional[int] = None,
    parse_mode: Optional[str] = None,
    card_id: Optional[str] = None,
    action: Optional[str] = None,
) -> bool:
    """Отправляет уведомление пользователю в Telegram.

    Args:
        telegram_id: Telegram user/chat ID
        message: Текст уведомления
        reply_to: reply_to_message_id
        parse_mode: parse mode (HTML, Markdown, ...)
        card_id: Если указан — добавляет кнопку «Просмотреть задачу»
        action: Если указан — после отправки обновляет сцены с page_name=action
    """
    try:
        tg = _get_tg()
        if not tg:
            return False

        list_markup = [
            {'text': "🗑 Удалить уведомление", 'callback_data': "delete_message"}
        ]

        if card_id:
            try:
                bot_info = await tg.bot.get_me()
                view_link = f'https://t.me/{bot_info.username}?start=type-open-view_id-{card_id}'
                list_markup.insert(0, {'text': "👁 Просмотреть задачу", 'url': view_link})
            except Exception as e:
                logger.warning(f"Не удалось добавить кнопку просмотра задачи: {e}")

        result = await tg.send_message(
            chat_id=str(telegram_id),
            text=message,
            reply_to_message_id=reply_to,
            parse_mode=parse_mode,
            list_markup=list_markup,
        )

        if action:
            try:
                await update_scenes(page_name=action, action="update")
            except Exception as e:
                logger.warning(f"Не удалось обновить сцены по action={action}: {e}")

        return result.get("success", False)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {e}")
        return False


async def notify_users(
    user_ids,
    message: str,
    action: Optional[str] = None,
    card_id: Optional[str] = None,
) -> None:
    """Send notifications to multiple users. Accepts telegram_id (int) or user_id (UUID)."""
    from models.User import User

    user_ids = list(set(user_ids))

    for uid in user_ids:
        if uid is None:
            continue
        try:
            # UUID — ищем telegram_id
            if isinstance(uid, _UUID) or (isinstance(uid, str) and '-' in str(uid)):
                users = await User.find(user_id=_UUID(str(uid)))
                if users and users[0].telegram_id:
                    await notify_user(users[0].telegram_id, message, card_id=card_id, action=action)
            else:
                await notify_user(int(uid), message, card_id=card_id, action=action)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя {uid}: {e}")


async def update_task_scenes(card_id: str) -> int:
    return await update_scenes(
        scene_name=SceneNames.VIEW_TASK, data_key="task_id", data_value=str(card_id), action="update")


async def close_user_scene(user_id: int) -> int:
    return await update_scenes(users_id=[user_id], action="close")


async def close_card_related_scenes(card_id: str) -> int:
    return await update_scenes(data_key="task_id", data_value=str(card_id), action="close")


async def update_scenes(
    scene_name: Optional[str] = None,
    page_name: Optional[str] = None,
    data_key: Optional[str] = None,
    data_value: Optional[str] = None,
    action: str = "update",
    users_id: Optional[list] = None,
) -> int:
    from tg.oms.manager import scene_manager
    active_scenes = list(scene_manager._instances.values())
    updated_count = 0
    users = list(set(users_id)) if users_id else None

    for scene in active_scenes:
        match = True
        if scene_name and scene.__scene_name__ != scene_name:
            match = False
        if page_name and scene.current_page.__page_name__ != page_name:
            match = False
        if data_key and data_value:
            scene_value = scene.data.get('scene', {}).get(data_key)
            if str(scene_value) != str(data_value):
                match = False
        if users and scene.user_id not in users:
            match = False

        if match:
            try:
                if action == "close":
                    await scene.end()
                else:
                    await scene.update_message()
                updated_count += 1
            except Exception as e:
                from modules.logs import executors_logger
                executors_logger.warning(f"Failed to update scene for user {scene.user_id}: {e}")

    return updated_count


# ==================== Дополнительно ====================

async def forward_first_by_tags(
    source_chat_id: int,
    message_id: int,
    tags: list[str],
    source_client_key: Optional[str] = None,
) -> dict:
    tg = _get_tg()
    if not tg:
        return {"success": False, "error": "telegram_executor not found"}

    from modules.constants import CLIENTS
    forwarded = 0
    for client_key, client_cfg in CLIENTS.items():
        if source_client_key and client_key == source_client_key:
            continue
        client_tags = client_cfg.get('tags', [])
        if not any(t in tags for t in client_tags):
            continue
        target_chat = client_cfg.get('chat_id') or client_cfg.get('channel_id')
        if not target_chat:
            continue
        try:
            await tg.bot.forward_message(
                chat_id=target_chat,
                from_chat_id=source_chat_id,
                message_id=message_id
            )
            forwarded += 1
        except Exception:
            pass

    return {"success": True, "forwarded": forwarded}


async def send_leaderboard(
    chat_id: int,
    period: str = 'all',
    reply_to: Optional[int] = None,
    extra_text: Optional[str] = None,
) -> bool:
    tg = _get_tg()
    if not tg:
        return False

    from models.User import User
    from modules.utils import get_user_display_name

    users = await User.get_all() or []

    if period == 'month':
        field = 'task_per_month'
        period_name = 'месяц'
        emoji = '📅'
    elif period == 'year':
        field = 'task_per_year'
        period_name = 'год'
        emoji = '📆'
    else:
        field = 'tasks'
        period_name = 'всё время'
        emoji = '🏆'

    sorted_users = sorted(users, key=lambda u: getattr(u, field, 0) or 0, reverse=True)
    text_lines = [f"{emoji} <b>Лидерборд за {period_name}</b>\n"]
    medals = ['🥇', '🥈', '🥉']
    idx = -1
    for user in sorted_users[:10]:
        tasks_count = getattr(user, field, 0) or 0
        if tasks_count == 0:
            continue
        idx += 1
        name = get_user_display_name(user) if user.telegram_id else 'Неизвестный'
        position = medals[idx] if idx < 3 else f" {idx + 1}."
        text_lines.append(f"• {position} <b>{name}</b> — {tasks_count} задач")

    if len(text_lines) == 1:
        text_lines.append("\n<i>Пока нет данных для отображения.</i>")

    text = "\n".join(text_lines)
    if extra_text:
        text += f"\n\n{extra_text}"

    result = await tg.send_message(
        chat_id=str(chat_id), text=text,
        reply_to_message_id=reply_to,
        parse_mode='HTML'
    )
    return result.get("success", False)
