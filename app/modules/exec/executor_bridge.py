"""
Мост между brain-модулями и executor-ами.
Заменяет HTTP-взаимодействие с executors-api прямыми вызовами функций.

Инициализируется в main.py после старта executor_manager.
"""
from typing import Optional, TYPE_CHECKING

from tg.main import TelegramExecutor

if TYPE_CHECKING:
    from modules.exec.executors_manager import ExecutorManager

# Устанавливается при старте приложения в main.py
_executor_manager: Optional["ExecutorManager"] = None


def set_manager(manager: "ExecutorManager") -> None:
    """Зарегистрировать инициализированный ExecutorManager."""
    global _executor_manager
    _executor_manager = manager


def get_manager() -> Optional["ExecutorManager"]:
    """Получить ExecutorManager. None если ещё не инициализирован."""
    return _executor_manager


# ==================== Forum ====================

async def send_forum_message(card_id: str) -> dict:
    """
    Отправить сообщение карточки на форум.
    Заменяет: executors_api.post(ApiEndpoints.FORUM_SEND_MESSAGE, data={"card_id": card_id})
    """
    from modules.text_generators import forum_message
    return await forum_message(card_id)


async def update_forum_message(card_id: str) -> dict:
    """
    Обновить сообщение карточки на форуме.
    Заменяет: executors_api.post(ApiEndpoints.FORUM_UPDATE_MESSAGE, ...)
    """
    from modules.text_generators import forum_message
    return await forum_message(card_id)


async def delete_forum_message(card_id: str) -> bool:
    """
    Удалить сообщение карточки с форума.
    Заменяет: executors_api.delete(ApiEndpoints.FORUM_DELETE_MESSAGE.format(card_id))
    """
    from modules.text_generators import card_deleted
    result = await card_deleted(card_id)
    return result.get("success", False)


async def delete_forum_message_by_id(message_id: int) -> bool:
    """
    Удалить сообщение с форума по message_id.
    Заменяет: executors_api.delete(ApiEndpoints.FORUM_DELETE_MESSAGE_FOR_ID.format(message_id))
    """
    from modules.json_utils import open_settings
    manager = get_manager()
    if not manager:
        return False

    settings = open_settings() or {}
    group_forum = settings.get("group_forum", 0)

    tg = manager.get("telegram_executor")
    if not tg:
        return False

    result = await tg.delete_message(
        chat_id=str(group_forum),
        message_id=str(message_id)
    )
    return result.get("success", False)


# ==================== Complete Preview ====================

async def send_complete_preview(card_id: str, client_key: str) -> dict:
    """
    Отправить превью готового поста.
    Заменяет: executors_api.post(ApiEndpoints.COMPLETE_SEND_PREVIEW, ...)
    """
    from modules.text_generators import send_complete_preview as _send
    return await _send(card_id, client_key)


async def update_complete_preview(
    card_id: str,
    client_key: str,
    post_ids: Optional[list] = None,
    info_id: Optional[int] = None,
    entities: Optional[list] = None
) -> dict:
    """
    Обновить превью готового поста.
    Заменяет: executors_api.post(ApiEndpoints.COMPLETE_UPDATE_PREVIEW, ...)
    """
    from modules.text_generators import update_complete_preview as _update
    return await _update(card_id, client_key, post_ids=post_ids, info_id=info_id, entities=entities)


async def delete_complete_preview(
    info_ids: Optional[list] = None,
    post_ids: Optional[list] = None,
    entities: Optional[list] = None
) -> dict:
    """
    Удалить превью готового поста.
    Заменяет: executors_api.post(ApiEndpoints.COMPLETE_DELETE_PREVIEW, ...)
    """
    from modules.text_generators import delete_complete_preview as _delete
    return await _delete(info_ids=info_ids, post_ids=post_ids, entities=entities)


async def forward_first_by_tags(
    source_chat_id: int,
    message_id: int,
    tags: list[str],
    source_client_key: Optional[str] = None
) -> dict:
    """
    Переслать сообщение в каналы, соответствующие заданным тегам.
    Заменяет: executors_api.post(ApiEndpoints.FORUM_FORWARD_FIRST_BY_TAGS, ...)
    """
    manager = get_manager()
    if not manager:
        return {"success": False, "error": "ExecutorManager not initialized"}

    tg: TelegramExecutor = manager.get("telegram_executor")
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


# ==================== Notifications ====================

async def notify_user(user_id: int, message: str, 
                      reply_to: Optional[int] = None, 
                      parse_mode: Optional[str] = None) -> bool:
    """
    Отправить уведомление пользователю.
    Заменяет: executors_api.post(ApiEndpoints.NOTIFY_USER, data={"user_id": user_id, "message": message})
    """
    manager = get_manager()
    if not manager:
        return False

    tg = manager.get("telegram_executor")
    if not tg:
        return False

    list_markup = [
        {'text': "🗑 Удалить уведомление",
         'callback_data': f"delete_message"}
    ]

    result = await tg.send_message(
        chat_id=str(user_id), text=message,
        reply_to_message_id=reply_to,
        parse_mode=parse_mode,
        list_markup=list_markup
    )
    return result.get("success", False)


async def send_leaderboard(
    chat_id: int,
    period: str = 'all',
    reply_to: Optional[int] = None,
    extra_text: Optional[str] = None
) -> bool:
    """
    Сгенерировать и отправить таблицу лидеров.
    Заменяет: executors_api.post(ApiEndpoints.SEND_LEADERBOARD, ...)
    """
    manager = get_manager()
    if not manager:
        return False

    tg = manager.get("telegram_executor")
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


# ==================== Scenes ====================

async def update_scenes(
    scene_name: Optional[str] = None,
    page_name: Optional[str] = None,
    data_key: Optional[str] = None,
    data_value: Optional[str] = None,
    action: str = "update",
    users_id: Optional[list[int]] = None
) -> int:
    """
    Обновить/закрыть активные сцены с заданными критериями.
    Заменяет: executors_api.post(ApiEndpoints.UPDATE_SCENES, ...)
    """
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
