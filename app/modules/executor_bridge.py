"""
Мост между brain-модулями и executor-ами.
Заменяет HTTP-взаимодействие с executors-api прямыми вызовами функций.

Инициализируется в main.py после старта executor_manager.
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.executors_manager import ExecutorManager

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
    from global_modules.json_get import open_settings
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


async def forward_first_by_tags(tags: list[str]) -> dict:
    """
    Переслать первое сообщение по тегам.
    Заменяет: executors_api.post(ApiEndpoints.FORUM_FORWARD_FIRST_BY_TAGS, ...)
    """
    from modules.text_generators import forward_first_by_tags as _forward
    return await _forward(tags)


# ==================== Notifications ====================

async def notify_user(user_id: int, message: str) -> bool:
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

    result = await tg.send_message(chat_id=str(user_id), text=message)
    return result.get("success", False)


async def send_leaderboard(users_data: list) -> bool:
    """
    Отправить таблицу лидеров.
    Заменяет: executors_api.post(ApiEndpoints.SEND_LEADERBOARD, ...)
    """
    from modules.text_generators import send_leaderboard as _send
    return await _send(users_data)


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


# ==================== Posts ====================

async def send_post(
    card_id: str,
    client_key: str,
    content: str,
    tags: Optional[list[str]] = None,
    post_images: Optional[list[str]] = None,
    settings: Optional[dict] = None,
    entities: Optional[list[dict]] = None
) -> dict:
    """
    Отправить пост через нужного исполнителя.
    Заменяет: executors_api.post("/post/send", ...)
    """
    from modules.constants import CLIENTS
    from modules.post_generator import generate_post
    from modules.post_sender import download_files
    from modules.entities_sender import send_poll_preview, get_entities_for_client

    settings = settings or {}
    client_config = CLIENTS.get(client_key)
    if not client_config:
        return {"success": False, "error": f"Client {client_key} not found"}

    executor_name = client_config.get("executor_name") or client_config.get("executor")
    client_id = client_config.get("client_id")

    manager = get_manager()
    if not manager:
        return {"success": False, "error": "ExecutorManager not initialized"}

    executor = manager.get(executor_name)
    if not executor:
        return {"success": False, "error": f"Executor {executor_name} not found"}

    try:
        text = generate_post(content, tags or [], client_config)
        files = await download_files(post_images or [])

        # Отправка через конкретный executor (tg или vk)
        from tg.main import TelegramExecutor
        from vk.main import VKExecutor

        if isinstance(executor, TelegramExecutor):
            return await executor.send_post(client_id, text, files, entities or [], settings)
        elif isinstance(executor, VKExecutor):
            return await executor.send_post(client_id, text, files, settings)
        else:
            return {"success": False, "error": f"Unknown executor type: {type(executor)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
