import asyncio
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID as _UUID
from sqlalchemy.ext.asyncio import AsyncSession
from global_modules.classes.enums import CardStatus
from models.Card import Card
from models.User import User
from database.connection import session_factory
from global_modules.json_get import open_properties
from modules.kaiten import update_kaiten_card_field, kaiten, add_kaiten_comment
from modules.executors_client import (
    notify_users, update_scenes, update_forum_message,
    send_complete_preview, update_complete_preview, 
    delete_complete_preview
)
from modules.constants import SceneNames, PropertyNames
from modules.properties import multi_properties
from modules.scheduler import reschedule_post_tasks, reschedule_card_notifications
from modules.calendar import update_calendar_event
from modules.status_changers import to_edited


def get_content_for_client(card: Card, client_key: str) -> str:
    """
    Получить контент для конкретного клиента.
    Сначала пытается получить специфичный контент для клиента,
    если его нет - возвращает общий контент ('all'),
    если и его нет - возвращает description.
    
    Args:
        card: Карточка
        client_key: Ключ клиента
        
    Returns:
        str: Контент для клиента
    """
    content_dict = card.content if isinstance(card.content, dict) else {}
    
    # Сначала пытаемся получить специфичный контент
    content = content_dict.get(client_key)
    
    # Если нет - берём общий
    if not content:
        content = content_dict.get('all')
    
    # Если и его нет - берём description
    if not content:
        content = card.description or ""
    
    return content


async def on_name(
                  new_name: str,
                  card: Optional[Card] = None, 
                  card_id: Optional[_UUID] = None,
                  ):
    """ Обработчик изменения названия карточки.
    """

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(
                f"Карточка с card_id {card_id} не найдена")

    if not new_name or not new_name.strip():
        raise ValueError("Название карточки не может быть пустым")

    new_name = new_name.strip()
    comment = f"✏️ Название изменено:\n{card.name} → {new_name}"

    await update_kaiten_card_field(
        card.task_id, 'title', 
        new_name, comment
    )
    await card.update(name=new_name)

    listeners = [
        card.executor_id,
        card.editor_id
    ]

    await notify_users(listeners, comment, 'change-name')

    # Обновляем форум
    if card.forum_message_id:
        await update_forum_message(str(card.card_id))

    # Обновляем, только если выбрано редактирование карточки и страница главная
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK,
                      'main-page',
                      "task_id",
                      str(card.card_id),
                      )
    )

    # Обновляем, только если выбрана страница с деталями задачи
    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK,
                      'task-detail',
                      "selected_task",
                      str(card.card_id),
                      )
    )


async def on_description(
    new_description: str,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения описания карточки."""

    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    comment = f"📝 Описание обновлено:\n{new_description[:200]}"
    if len(new_description) > 200:
        comment += "..."

    if card.task_id and card.task_id != 0:
        await update_kaiten_card_field(
            card.task_id, 'description', 
            new_description, comment
        )

    await card.update(description=new_description)

    listeners = [
        card.executor_id,
        card.editor_id
    ]

    await notify_users(listeners, comment, 'change-description')

    # Обновляем форум
    if card.forum_message_id:
        await update_forum_message(str(card.card_id))

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page', 
                     "task_id", str(card.card_id))
    )

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_deadline(
    new_deadline: datetime,
    old_deadline: Optional[datetime] = None,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения дедлайна карточки."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    # Формируем комментарий
    if old_deadline:
        comment = f"⏰ Дедлайн изменен: {old_deadline.strftime('%d.%m.%Y %H:%M')} → {new_deadline.strftime('%d.%m.%Y %H:%M')}"
    else:
        comment = f"⏰ Дедлайн установлен: {new_deadline.strftime('%d.%m.%Y %H:%M')}"

    # Обновляем в Kaiten
    if card.task_id and card.task_id != 0:
        await update_kaiten_card_field(
            card.task_id, 'due_date',
            new_deadline.strftime('%Y-%m-%d'),
            comment
        )

    # Обновляем в календаре
    if card.calendar_id:
        try:
            await update_calendar_event(
                event_id=card.calendar_id,
                start_time=new_deadline
            )
        except Exception as e:
            print(f"Error updating calendar event: {e}")

    # Обновляем карточку
    await card.update(deadline=new_deadline)

    # Перепланируем напоминания
    try:
        async with session_factory() as session:
            await card.refresh()
            await reschedule_card_notifications(session, card)
    except Exception as e:
        print(f"Error rescheduling card notifications: {e}")

    # Уведомляем участников
    listeners = [
        card.executor_id,
        card.editor_id,
        card.customer_id
    ]

    await notify_users(listeners, comment, 'change-deadline')

    # Обновляем форум
    if card.forum_message_id:
        await update_forum_message(str(card.card_id))

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_send_time(
    new_send_time: Optional[datetime],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения времени публикации."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(send_time=new_send_time)

    # Перепланируем задачи публикации
    try:
        async with session_factory() as session:
            await card.refresh()
            await reschedule_post_tasks(session, card)
            print(f"Rescheduled post tasks for card {card.card_id}")
    except Exception as e:
        print(f"Error rescheduling post tasks: {e}")

    # Обновляем превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            clients = card.clients or []
            
            for client_key in clients:
                if client_key in complete_message_ids:
                    msg_data = complete_message_ids[client_key]
                    if isinstance(msg_data, dict):
                        await update_complete_preview(
                            str(card.card_id), client_key,
                            msg_data.get("post_id"),
                            msg_data.get("post_ids", []),
                            msg_data.get("info_id")
                        )
        except Exception as e:
            print(f"Error updating complete previews: {e}")

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_executor(
    new_executor_id: Optional[_UUID],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения исполнителя."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    old_executor_id = card.executor_id
    forum_upd = False
    
    # Обрабатываем старого исполнителя (если есть)
    if old_executor_id and old_executor_id != new_executor_id:
        old_user = await User.get_by_key('user_id', old_executor_id)
        if old_user:
            # Закрываем сцену если это не заказчик
            if old_executor_id != card.customer_id:
                from modules.executors_client import close_user_scene
                await close_user_scene(old_user.telegram_id)
            
            # Удаляем из Kaiten
            if card.task_id and card.task_id != 0 and old_user.tasker_id:
                async with kaiten as client:
                    await client.remove_card_member(card.task_id, old_user.tasker_id)
    
    # Обновляем исполнителя в БД
    await card.update(executor_id=new_executor_id)
    
    # Обрабатываем нового исполнителя
    kaiten_comment = None
    if new_executor_id is None:
        kaiten_comment = "❌ Исполнитель удален"
    else:
        new_user = await User.get_by_key('user_id', new_executor_id)
        if new_user:
            # Добавляем в Kaiten
            if card.task_id and card.task_id != 0 and new_user.tasker_id:
                async with kaiten as client:
                    card_k = await client.get_card(card.task_id)
                    if card_k:
                        members = await card_k.get_members()
                        member_ids = [m['id'] for m in members]
                        
                        if new_user.tasker_id not in member_ids:
                            await client.add_card_member(card.task_id, new_user.tasker_id)

            # Уведомляем нового исполнителя
            await notify_users([new_executor_id], 
                f"📝 Вы назначены исполнителем задачи: {card.name}",
                'assign-executor')

            kaiten_comment = f"👤 Исполнитель назначен: {await new_user.name() if await new_user.name() else 'Неизвестный'}"

            if card.status == CardStatus.pass_:
                forum_upd = True
                await to_edited(card)

    # Добавляем комментарий в Kaiten
    if kaiten_comment and card.task_id and card.task_id != 0:
        await add_kaiten_comment(card.task_id, kaiten_comment)

    # Обновляем форум
    if card.forum_message_id and not forum_upd:
        await update_forum_message(str(card.card_id))

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )
    
    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_editor(
    new_editor_id: Optional[_UUID],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения редактора."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем редактора
    await card.update(editor_id=new_editor_id)
    
    # Комментарий в Kaiten
    if card.task_id and card.task_id != 0 and new_editor_id:
        editor = await User.get_by_key('user_id', new_editor_id)
        editor_name = await editor.name() if editor else "Неизвестный"
        comment = f"✏️ Редактор назначен: {editor_name}"
        await add_kaiten_comment(card.task_id, comment)

    # Уведомляем нового редактора
    if new_editor_id:
        await notify_users([new_editor_id],
                          f"📝 Вы назначены редактором задачи: {card.name}",
                          'editor-assigned')

    if card.forum_message_id:
        await update_forum_message(str(card.card_id))

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_content(
    new_content: str,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None,
    client_key: Optional[str] = None
):
    """
    Обработчик изменения контента поста.
    
    Args:
        new_content: Новый контент
        card: Объект карточки
        card_id: ID карточки (если card не передан)
        client_key: Ключ клиента. Если None - устанавливается общий контент (ключ 'all'), 
                    если указан - контент для конкретного клиента
    """
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")

    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    # Получаем текущий content dict (или создаем пустой)
    content_dict = card.content if isinstance(card.content, dict) else {}
    
    # Если client_key не указан, используем ключ 'all' для общего контента
    key = client_key if client_key else 'all'
    
    # Обновляем контент
    content_dict[key] = new_content
    
    # Сохраняем обновленный content dict
    await card.update(content=content_dict)

    # Обновляем превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            clients = card.clients or []
            
            for client_key in clients:
                if client_key in complete_message_ids:
                    msg_data = complete_message_ids[client_key]
                    if isinstance(msg_data, dict):
                        update_res = await update_complete_preview(
                            str(card.card_id), client_key,
                            msg_data.get("post_id"),
                            msg_data.get("post_ids", []),
                            msg_data.get("info_id")
                        )
                        if update_res.get("post_id"):
                            complete_message_ids[client_key] = {
                                "post_id": update_res.get("post_id"),
                                "post_ids": update_res.get("post_ids", []),
                                "info_id": update_res.get("info_id")
                            }
            
            await card.update(complete_message_id=complete_message_ids)
        except Exception as e:
            print(f"Error updating complete previews: {e}")

async def on_clients(
    new_clients: list[str],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения списка каналов для публикации."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем в Kaiten
    if card.task_id and card.task_id != 0:
        props = open_properties() or {}
        new_channels = []
        for channel in new_clients:
            if str(channel).isdigit():
                new_channels.append(int(channel))
            else:
                new_channels.append(
                    props[PropertyNames.CHANNELS]['values'][channel]['id']
                )

        try:
            async with kaiten as client:
                await client.update_card(
                    card.task_id,
                    properties=multi_properties(channels=new_channels)
                )
        except Exception as e:
            print(f"Error updating channels in Kaiten: {e}")

    # Обновляем карточку
    old_clients = set(card.clients or [])
    removed_clients = old_clients - set(new_clients)
    
    # Удаляем из clients_settings клиентов, которых больше нет
    for client_key in removed_clients:
        card.clients_settings.pop(client_key, None)
    
    # Добавляем новых клиентов в clients_settings
    for client_key in new_clients:
        if client_key not in card.clients_settings.keys():
            card.clients_settings[client_key] = {}
    
    # Обновляем content dict - удаляем ключи удаленных клиентов
    content_dict = card.content if isinstance(card.content, dict) else {}
    for client_key in removed_clients:
        content_dict.pop(client_key, None)

    await card.update(
        clients=new_clients, 
        clients_settings=card.clients_settings,
        content=content_dict
    )

    # Перепланируем задачи публикации
    try:
        async with session_factory() as session:
            await card.refresh()
            await reschedule_post_tasks(session, card)
    except Exception as e:
        print(f"Error rescheduling post tasks: {e}")
    
    # Обновляем превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            
            # Удаляем превью для клиентов, которых больше нет
            for client_key in list(complete_message_ids.keys()):
                if client_key not in new_clients:
                    msg_data = complete_message_ids.pop(client_key)
                    if isinstance(msg_data, dict):
                        await delete_complete_preview(
                            post_id=msg_data.get("post_id"),
                            post_ids=msg_data.get("post_ids"),
                            info_id=msg_data.get("info_id")
                        )
            
            # Добавляем превью для новых клиентов
            for client_key in new_clients:
                if client_key not in complete_message_ids:
                    preview_res = await send_complete_preview(str(card.card_id), client_key)
                    if preview_res.get("success"):
                        complete_message_ids[client_key] = {
                            "post_id": preview_res.get("post_id"),
                            "post_ids": preview_res.get("post_ids", []),
                            "info_id": preview_res.get("info_id")
                        }
            
            await card.update(complete_message_id=complete_message_ids)
        except Exception as e:
            print(f"Error updating complete previews: {e}")

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_need_check(
    need_check: bool,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения флага необходимости проверки."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем в Kaiten
    if card.task_id and card.task_id != 0:
        try:
            async with kaiten as client:
                await client.update_card(
                    card.task_id,
                    properties=multi_properties(editor_check=need_check)
                )
        except Exception as e:
            print(f"Error updating need_check in Kaiten: {e}")
    
    # Обновляем карточку
    await card.update(need_check=need_check)
    
    # Обновляем форум
    if card.forum_message_id:
        await update_forum_message(str(card.card_id))
    
    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_tags(
    new_tags: list[str],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения тегов."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем в Kaiten
    if card.task_id and card.task_id != 0:
        props = open_properties() or {}
        kaiten_tags = []
        for tag in new_tags:
            if str(tag).isdigit():
                kaiten_tags.append(int(tag))
            else:
                kaiten_tags.append(
                    props[PropertyNames.TAGS]['values'][tag]['id']
                )
        
        try:
            async with kaiten as client:
                await client.update_card(
                    card.task_id,
                    properties=multi_properties(tags=kaiten_tags)
                )
        except Exception as e:
            print(f"Error updating tags in Kaiten: {e}")
    
    # Обновляем карточку
    await card.update(tags=new_tags)
    
    # Обновляем превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            clients = card.clients or []
            
            for client_key in clients:
                if client_key in complete_message_ids:
                    msg_data = complete_message_ids[client_key]
                    if isinstance(msg_data, dict):
                        await update_complete_preview(
                            str(card.card_id), client_key,
                            msg_data.get("post_id"),
                            msg_data.get("post_ids", []),
                            msg_data.get("info_id")
                        )
        except Exception as e:
            print(f"Error updating complete previews: {e}")
    
    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    # Обновляем форум
    if card.forum_message_id:
        await update_forum_message(str(card.card_id))

    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_image_prompt(
    new_prompt: Optional[str],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения промпта для изображения."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")

    # Обновляем карточку
    await card.update(image_prompt=new_prompt)

async def on_prompt_message(
    message_id: int,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения ID сообщения с промптом для дизайнеров."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(prompt_message=message_id)

async def on_forum_message_id(
    forum_message_id: Optional[int],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения ID сообщения на форуме."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(forum_message_id=forum_message_id)

async def on_complete_message_id(
    complete_message_id: dict,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения словаря с ID превью готовых постов."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(complete_message_id=complete_message_id)

async def on_editor_notes(
    editor_notes: list[dict],
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения заметок редактора."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(editor_notes=editor_notes)
    
    # Уведомляем исполнителя о новой заметке
    if card.executor_id and editor_notes:
        last_note = editor_notes[-1] if editor_notes else None
        if last_note:
            note_text = last_note.get('content', '')
            await notify_users([card.executor_id],
                             f"📋 Новая заметка редактора:\n{note_text[:256]}",
                             'editor-notes')

    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'editor-notes',
                     "task_id", str(card.card_id))
    )

async def on_clients_settings(
    clients_settings: dict,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения настроек для клиентов (шаблоны подписей, сетка для VK и т.д.)."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(clients_settings=clients_settings)
    
    # Обновляем превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            clients = card.clients or []
            
            for client_key in clients:
                if client_key in complete_message_ids:
                    msg_data = complete_message_ids[client_key]
                    if isinstance(msg_data, dict):
                        await update_complete_preview(
                            str(card.card_id), client_key,
                            msg_data.get("post_id"),
                            msg_data.get("post_ids", []),
                            msg_data.get("info_id")
                        )
        except Exception as e:
            print(f"Error updating complete previews: {e}")
    
    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )
    
    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )

async def on_entities(
    entities: dict,
    card: Optional[Card] = None, 
    card_id: Optional[_UUID] = None
):
    """Обработчик изменения entities для клиентов (опросы в Telegram, авто-репост и т.д.)."""
    
    if not card_id and not card:
        raise ValueError("Необходимо указать card или card_id")
    
    if not card:
        card = await Card.get_by_key('card_id', str(card_id))
        if not card:
            raise ValueError(f"Карточка с card_id {card_id} не найдена")
    
    # Обновляем карточку
    await card.update(entities=entities)
    
    # Обновляем превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            clients = card.clients or []
            
            for client_key in clients:
                if client_key in complete_message_ids:
                    msg_data = complete_message_ids[client_key]
                    if isinstance(msg_data, dict):
                        await update_complete_preview(
                            str(card.card_id), client_key,
                            msg_data.get("post_id"),
                            msg_data.get("post_ids", []),
                            msg_data.get("info_id")
                        )
        except Exception as e:
            print(f"Error updating complete previews: {e}")
    
    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )
    
    await asyncio.create_task(
        update_scenes(SceneNames.VIEW_TASK, 'task-detail',
                     "selected_task", str(card.card_id))
    )