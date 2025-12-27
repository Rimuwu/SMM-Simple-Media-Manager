from modules.api_client import executors_api
from modules.constants import ApiEndpoints, SceneNames
from modules.logs import brain_logger as logger
from uuid import UUID as _UUID
from models.User import User
from models.Card import Card
from models.CardMessage import CardMessage
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

# ==================== Форум ====================

async def send_forum_message(
    card_id: str) -> tuple[int | None, str | None]:
    """
    Отправить сообщение о карточке в форум.

    Returns:
        tuple: (message_id или None, error или None)
    """
    try:
        forum_res, status = await executors_api.post(
            ApiEndpoints.FORUM_SEND_MESSAGE,
            data={"card_id": card_id}
        )

        error = forum_res.get('error')
        if error:
            logger.error(f"Ошибка отправки в форум: {error}")
            return None, error

        return forum_res.get("message_id"), None
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в форум: {e}")
        return None, str(e)


async def update_forum_message(
    card_id: str
    ) -> tuple[int | None, str | None]:
    """
    Обновить сообщение на форуме.

    Args:
        card_id: ID карточки

    Returns:
        tuple: (message_id или None, error или None)
    """
    try:
        forum_res, _ = await executors_api.post(
            ApiEndpoints.FORUM_UPDATE_MESSAGE,
            data={"card_id": card_id}
        )
        if forum_res.get('error'):
            logger.error(
                f"Ошибка обновления сообщения форума: {forum_res.get('error')}")
            return None, forum_res.get('error')

        message_id, error = forum_res.get("message_id"), forum_res.get("error")

        card = await Card.get_by_id(
            _UUID(card_id)
        )
        if card:
            card_message = await card.get_forum_message()
            if not card_message and message_id:
                await CardMessage(
                    card_id=card.card_id,
                    message_type='forum',
                    message_id=message_id
                )
            elif card_message and card_message.message_id != message_id and message_id:
                await card_message.update(
                    message_id=message_id
                )
        return message_id, error

    except Exception as e:
        logger.error(f"Ошибка обновления сообщения форума: {e}")
        return None, str(e)


async def delete_forum_message(card_id: str) -> bool:
    """
    Удалить сообщение с форума по card_id.
    
    Returns:
        True если успешно
    """
    try:
        await executors_api.delete(
            ApiEndpoints.FORUM_DELETE_MESSAGE.value.format(card_id)
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения форума: {e}")
        return False


async def delete_forum_message_by_id(message_id: int) -> bool:
    """
    Удалить сообщение с форума по message_id.

    Returns:
        True если успешно
    """
    try:
        forum_res, _ = await executors_api.delete(
            ApiEndpoints.FORUM_DELETE_MESSAGE_FOR_ID.value.format(message_id)
        )
        return forum_res.get('success', False)
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения форума по ID: {e}")
        return False


# ==================== Complete Preview (Превью готовых постов) ====================

async def send_complete_preview(
    card_id: str, 
    client_key: str,
    session: Optional[AsyncSession] = None
    ) -> dict:
    """
    Отправить превью готового поста в complete_topic и создать записи в БД.

    Если передана `session`, операции с БД выполняются в ней.

    Returns:
        dict: {"success": bool, "post_ids": list, "entities": list, "info_id": int, "error": str}
    """
    try:
        preview_res, _ = await executors_api.post(
            ApiEndpoints.COMPLETE_SEND_PREVIEW,
            data={
                "card_id": card_id,
                "client_key": client_key
            }
        )

        if preview_res.get('success') is True:
            card = await Card.get_by_id(_UUID(card_id))
            if card:
                post_ids = preview_res.get("post_ids") or []  # Посты с медиа-группами
                entities = preview_res.get("entities", [])  # Список id сущностей
                info_id = preview_res.get("info_id")  # Инфа сообщение

                # Создаём записи в БД: используем переданную сессию если есть
                if session:
                    for pid in post_ids:
                        await card.add_complete_post_message(message_id=pid, data_info=client_key, session=session)

                    if info_id is not None:
                        await card.add_complete_info_message(message_id=int(info_id), data_info=client_key, session=session)

                    for eid in entities:
                        if eid is not None:
                            await card.add_complete_entity_message(message_id=int(eid), data_info=client_key, session=session)
                else:
                    for pid in post_ids:
                        await card.add_complete_post_message(message_id=pid, data_info=client_key)

                    if info_id is not None:
                        await card.add_complete_info_message(message_id=int(info_id), data_info=client_key)

                    for eid in entities:
                        if eid is not None:
                            await card.add_complete_entity_message(message_id=int(eid), data_info=client_key)

        return {
            "success": preview_res.get("success", False), # Выполнено ли
            "post_ids": preview_res.get("post_ids"), # Посты с медиа-группами
            "entities": preview_res.get("entities", []), # Список id сущностей
            "info_id": preview_res.get("info_id"), # Инфа сообщение
            "error": preview_res.get("error")
        }
    except Exception as e:
        logger.error(f"Ошибка отправки complete preview: {e}")
        return {"success": False, "error": str(e)}


async def update_complete_preview(
    card_id: str, 
    client_key: str, 
    post_ids: list[int] | None = None,
    entities: list[int] | None = None,
    info_id: int | None = None,
    session: Optional[AsyncSession] = None
    ) -> dict:
    """
    Обновить превью готового поста в complete_topic и синхронизировать записи в БД если передана сессия.

    Returns:
        dict: {"success": bool, "post_ids": list, "info_id": int, "entities": list, "error": str}
    """
    try:
        data = {
            "card_id": card_id,
            "client_key": client_key,
            "post_ids": post_ids,
            "entities": entities,
            "info_id": info_id
        }
        update_res, _ = await executors_api.post(
            ApiEndpoints.COMPLETE_UPDATE_PREVIEW,
            data=data
        )

        # При необходимости синхронизируем БД (если передана сессия)
        if session and update_res.get('success'):
            card = await Card.get_by_id(_UUID(card_id))
            if card:
                # Получаем существующие сообщения для клиента
                msgs = await card.get_complete_messages_by_client(client_key=client_key, session=session)
                existing_posts = [m for m in msgs if m.message_type == 'complete_post']
                existing_info = next((m for m in msgs if m.message_type == 'complete_info'), None)

                returned_post_ids = update_res.get('post_ids') or []
                returned_post_ids = [int(pid) for pid in returned_post_ids if pid is not None]

                # Синхронизация post ids
                if returned_post_ids:
                    if len(returned_post_ids) == len(existing_posts):
                        for m, pid in zip(existing_posts, returned_post_ids):
                            if int(m.message_id) != pid:
                                await m.update(session=session, message_id=pid)
                    else:
                        for m in existing_posts:
                            await m.delete(session=session)
                        for pid in returned_post_ids:
                            await card.add_complete_post_message(message_id=pid, data_info=client_key, session=session)

                # Info
                returned_info_id = update_res.get('info_id')
                if returned_info_id is not None:
                    if existing_info:
                        await existing_info.update(session=session, message_id=int(returned_info_id))
                    else:
                        await card.add_complete_info_message(message_id=int(returned_info_id), data_info=client_key, session=session)

                # Entities — пересоздаём
                returned_entities = update_res.get('entities', []) or []
                if returned_entities:
                    # удаляем старые entity
                    for m in [m for m in msgs if m.message_type == 'complete_entity']:
                        await m.delete(session=session)
                    for eid in returned_entities:
                        if eid is not None:
                            await card.add_complete_entity_message(message_id=int(eid), data_info=client_key, session=session)

        return {
            "success": update_res.get("success", True),  # Считаем успехом если нет ошибки
            "post_ids": update_res.get("post_ids"),
            "entities": update_res.get("entities", []),
            "info_id": update_res.get("info_id"),
            "error": update_res.get("error")
        }
    except Exception as e:
        logger.error(f"Ошибка обновления complete preview: {e}")
        return {"success": False, "error": str(e)}


async def delete_complete_preview(
    post_ids: list[int] | None = None,
    entities: list[int] | None = None,
    info_ids: list[int] | None = None,
    card_id: str | None = None,
    session: Optional[AsyncSession] = None
    ) -> bool:
    """
    Удалить превью готового поста из complete_topic и удалить записи из БД (если передана сессия или card_id).
    
    Returns:
        True если успешно
    """
    try:
        data = {}
        if post_ids is not None:
            data["post_ids"] = post_ids
        elif entities is not None:
            data["entities"] = entities
        if info_ids is not None:
            data["info_ids"] = info_ids

        await executors_api.post(
            ApiEndpoints.COMPLETE_DELETE_PREVIEW,
            data=data
        )

        # Удаляем записи из БД если передано card_id или session
        from models.CardMessage import CardMessage
        if session:
            if post_ids:
                for pid in post_ids:
                    msgs = await CardMessage.filter_by(session=session, message_type='complete_post', message_id=pid)
                    for m in msgs:
                        await m.delete(session=session)
            if entities:
                for eid in entities:
                    msgs = await CardMessage.filter_by(session=session, message_type='complete_entity', message_id=eid)
                    for m in msgs:
                        await m.delete(session=session)
            if info_id is not None:
                msgs = await CardMessage.filter_by(session=session, message_type='complete_info', message_id=info_id)
                for m in msgs:
                    await m.delete(session=session)

        elif card_id:
            # если передан card_id, удаляем записи, ограничивая карточкой
            card = await Card.get_by_id(_UUID(card_id))
            if card:
                msgs = await card.get_complete_preview_messages()
                if post_ids:
                    for m in [m for m in msgs if m.message_type == 'complete_post' and int(m.message_id) in post_ids]:
                        await m.delete()
                if entities:
                    for m in [m for m in msgs if m.message_type == 'complete_entity' and int(m.message_id) in entities]:
                        await m.delete()
                if info_id is not None:
                    for m in [m for m in msgs if m.message_type == 'complete_info' and int(m.message_id) == info_id]:
                        await m.delete()

        return True
    except Exception as e:
        logger.error(f"Ошибка удаления complete preview: {e}")
        return False


async def delete_all_complete_previews(
    complete_messages: list
    ) -> bool:
    """
    Удалить все превью для карточки.

    Args:
        complete_messages: Список объектов CardMessage (mix of complete_post/complete_info/complete_entity)

    Returns:
        True если все удалены успешно
    """
    success = True

    # Группируем по client_key (data_info) чтобы удалить посты и info в одной операции
    groups: dict[str, list] = {}
    for msg in complete_messages:
        key = msg.data_info or '__none__'
        groups.setdefault(key, []).append(msg)

    from database.connection import session_factory
    for key, msgs in groups.items():
        try:
            post_ids = [int(m.message_id) for m in msgs if m.message_type == 'complete_post']
            info_ids = [int(m.message_id) for m in msgs if m.message_type == 'complete_info']
            entity_ids = [int(m.message_id) for m in msgs if m.message_type == 'complete_entity']

            # Используем сессию для атомарности: удаляем remote и БД внутри сессии
            async with session_factory() as s:
                if post_ids or info_ids:
                    await delete_complete_preview(post_ids=post_ids or None, 
                                                  entities=entity_ids or None,
                                                  info_ids=info_ids or None, 
                                                  session=s
                                                  )

                await s.commit()

        except Exception as e:
            logger.error(f"Ошибка удаления complete preview: {e}")
            success = False

    return success


# ==================== Сцены ====================

async def update_scenes(
    scene_name: str | None = None,
    page_name: str | None = None,
    data_key: str | None = None,
    data_value: str | None = None
    ) -> bool:
    """
    Обновить (перезагрузить) активные сцены по критериям.
    
    Returns:
        True если успешно
    """
    try:
        data = {}
        if scene_name:
            data["scene_name"] = scene_name
        if page_name:
            data["page_name"] = page_name
        if data_key:
            data["data_key"] = data_key
        if data_value:
            data["data_value"] = data_value

        await executors_api.post(
            ApiEndpoints.UPDATE_SCENES, data=data)
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления сцен: {e}")
        return False

async def update_task_scenes(
    card_id: str, scene_name: str = SceneNames.USER_TASK) -> bool:
    """
    Обновить все сцены, связанные с задачей.

    Args:
        card_id: ID карточки
        scene_name: Имя сцены (по умолчанию user-task)

    Returns:
        True если успешно
    """
    return await update_scenes(
        scene_name=scene_name,
        data_key="task_id",
        data_value=card_id
    )


async def close_card_related_scenes(card_id: str) -> bool:
    """
    Закрыть все сцены, связанные с карточкой (user-task и task-detail).

    Returns:
        True если все закрыты успешно
    """

    try:
        await executors_api.post(
            ApiEndpoints.UPDATE_SCENES,
                {
                    "scene_name": SceneNames.USER_TASK,
                    "data_key": "task_id",
                    "data_value": card_id,
                    "action": "close"
                }
            )
        await executors_api.post(
            ApiEndpoints.UPDATE_SCENES,
                {
                    "scene_name": SceneNames.VIEW_TASK,
                    "page_name": "task-detail",
                    "data_key": "selected_task",
                    "data_value": card_id,
                    "action": "update"
                }
            )
        return True
    except Exception as e:
        logger.error(
            f"Ошибка закрытия связанных сцен: {e}"
            )
        return False


async def close_user_scene(telegram_id: int, 
                           scene_name: str | None = None
                           ) -> bool:
    """
    Закрыть все сцены пользователя.

    Returns:
        True если успешно
    """

    try:
        await executors_api.post(
            ApiEndpoints.UPDATE_SCENES,
                {
                    "users_id": [telegram_id],
                    "scene_name": scene_name,
                    "action": "close"
                }
            )
        return True
    except Exception as e:
        logger.error(
            f"Ошибка закрытия сцены пользователя {telegram_id}: {e}"
            )
        return False

# ==================== Уведомления ====================

async def notify_user(telegram_id: int, 
                      message: str,
                      skip_if_page: str | None | list[str] = None
                      ) -> bool:
    """
    Отправить уведомление пользователю.
    Args:
        telegram_id: Telegram ID пользователя
        message: Текст сообщения
        skip_if_page: Пропустить уведомление, если пользователь на этой странице
    Returns:
        True если успешно
    """
    try:
        data = {"user_id": telegram_id, "message": message}
        if skip_if_page:
            data["skip_if_page"] = skip_if_page

        await executors_api.post(
            ApiEndpoints.NOTIFY_USER,
            data=data
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {e}")
        return False


async def notify_users(users: list[_UUID | None], 
                       message: str,
                       skip_if_page: str | None | list[str] = None
                       ) -> int:
    """
    Отправить уведомление списку пользователей.

    Args:
        users: Список объектов User с атрибутом telegram_id
        message: Текст сообщения

    Returns:
        Количество успешно отправленных уведомлений
    """
    success_count = 0
    users = list(set(users))  # Убираем дубликаты

    for user_id in users:
        if user_id is None: continue

        user = await User.get_by_key('user_id', user_id)
        if not user or not user.telegram_id:
            continue

        if await notify_user(user.telegram_id, message, skip_if_page):
            success_count += 1

    return success_count

