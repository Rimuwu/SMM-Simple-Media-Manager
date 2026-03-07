import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID as _UUID
from global_modules.classes.enums import CardStatus
from models.Card import Card
from models.User import User
from database.connection import session_factory
from modules.executors_client import (
    notify_users, update_scenes, update_forum_message,
    send_complete_preview, update_complete_preview, 
    delete_complete_preview, delete_all_complete_previews
)
from modules.constants import SceneNames
from modules.scheduler import reschedule_post_tasks, reschedule_card_notifications
from modules.calendar import update_calendar_event
from modules.status_changers import to_edited
from models.CardEditorNote import CardEditorNote
from modules.logs import logger


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
    await card.update(name=new_name)

    listeners = [
        card.executor_id,
        card.editor_id
    ]

    await notify_users(listeners, comment, 'change-name')

    # Обновляем форум
    if await card.get_forum_message():
        message_id, error = await update_forum_message(
            str(card.card_id))

    if card.calendar_id:
        await update_calendar_event(
            card.calendar_id,
            title=new_name
        )

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

    await card.update(description=new_description)

    if card.calendar_id:
        await update_calendar_event(
            card.calendar_id,
            description=new_description
        )

    listeners = [
        card.executor_id,
        card.editor_id
    ]

    await notify_users(listeners, comment, 'change-description')

    # Обновляем форум
    if await card.get_forum_message():
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

    # Обновляем в календаре
    if card.calendar_id and card.send_time is None:
        try:
            await update_calendar_event(
                event_id=card.calendar_id,
                start_time=new_deadline,
                end_time=new_deadline + timedelta(minutes=60)
            )
        except Exception as e:
            logger.error(f"Ошибка обновления события календаря для карточки {card.card_id}: {e}")

    # Обновляем карточку
    await card.update(deadline=new_deadline)

    # Перепланируем напоминания
    try:
        async with session_factory() as session:
            await card.refresh()
            await reschedule_card_notifications(session, card)
    except Exception as e:
        logger.error(f"Ошибка перепланирования уведомлений для карточки {card.card_id}: {e}")

    # Уведомляем участников
    listeners = [
        card.executor_id,
        card.editor_id,
        card.customer_id
    ]

    await notify_users(listeners, comment, 'change-deadline')

    # Обновляем форум
    if await card.get_forum_message():
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
            logger.info(f"Задачи публикации перепланированы для карточки {card.card_id}")
    except Exception as e:
        logger.error(f"Ошибка перепланирования задач публикации для карточки {card.card_id}: {e}")

    # Обновляем превью если карточка готова — удаляем все и создаём новые
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")

    if card.calendar_id and new_send_time:
        await update_calendar_event(
            card.calendar_id,
            start_time=new_send_time,
            end_time=new_send_time + timedelta(minutes=60)
        )

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
            

    
    # Обновляем исполнителя в БД
    await card.update(executor_id=new_executor_id)
    
    # Обрабатываем нового исполнителя
    if new_executor_id is None:
        pass
    else:
        new_user = await User.get_by_key('user_id', new_executor_id)
        if new_user:
            # Уведомляем нового исполнителя
            await notify_users([new_executor_id], 
                f"📝 Вы назначены исполнителем задачи: {card.name}",
                'assign-executor')

            if card.status == CardStatus.pass_:
                forum_upd = True
                await to_edited(card)

    # Обновляем форум
    if await card.get_forum_message() and not forum_upd:
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

    # Уведомляем нового редактора
    if new_editor_id:
        await notify_users([new_editor_id],
                          f"📝 Вы назначены редактором задачи: {card.name}",
                          'editor-assigned')

    if await card.get_forum_message():
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

    # Если client_key не указан, используем общий контент (client_key=None)
    key = client_key if client_key else None

    # Создаём или обновляем запись в таблице CardContent
    from models.CardContent import CardContent
    content_records = await CardContent.filter_by(
        card_id=card.card_id,
        client_key=key
    )
    if content_records:
        content_record = content_records[0]
        await content_record.update(text=new_content)
    else:
        await CardContent.create(
            card_id=card.card_id,
            client_key=key,
            text=new_content
        )

    # Обновляем превью если карточка готова — удаляем все и создаём новые
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")

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
    
    # Обновляем карточку
    old_clients = set(card.clients or [])
    removed_clients = old_clients - set(new_clients)
    
    # Удаляем настройки и контент клиентов, которых больше нет
    from models.ClientSetting import ClientSetting
    for client_key in removed_clients:
        settings = await card.get_clients_settings(client_key=client_key)
        for s in settings:
            await s.delete()
        # Удаляем контент
        contents = await card.get_content(client_key=client_key)
        for c in contents:
            await c.delete()

    # Добавляем новых клиентов (пустые настройки) если их ещё нет
    for client_key in new_clients:
        settings = await card.get_clients_settings(client_key=client_key)
        if not settings:
            await card.set_client_setting(client_key=client_key, data={}, type=None)

    await card.update(clients=new_clients)

    # Перепланируем задачи публикации
    try:
        async with session_factory() as session:
            await card.refresh()
            await reschedule_post_tasks(session, card)
    except Exception as e:
        logger.error(f"Ошибка перепланирования задач публикации для карточки {card.card_id}: {e}")

    # Обновляем превью если карточка готова — удаляем все и создаём новые
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")

    # Обновляем форум
    if await card.get_forum_message():
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
    
    # Обновляем карточку
    await card.update(need_check=need_check)
    
    # Обновляем форум
    if await card.get_forum_message():
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
    
    # Обновляем карточку
    await card.update(tags=new_tags)
    
    # Обновляем превью если карточка готова — удаляем все и создаём новые
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")
    
    # Обновляем сцены
    await asyncio.create_task(
        update_scenes(SceneNames.USER_TASK, 'main-page',
                     "task_id", str(card.card_id))
    )

    # Обновляем форум
    if await card.get_forum_message():
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

    # При изменении промпта на изображение — пересоздаём превью если карточка готова
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")

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

async def on_editor_notes(
    content: str,
    author: str,
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
    await CardEditorNote.create(
        card_id=card.card_id,
        author=author,
        content=content
    )

    # Уведомляем исполнителя о новой заметке
    if card.executor_id and card.executor_id != author:
        await notify_users([card.executor_id],
                            f"📋 Новая заметка редактора:\n{content[:256]}",
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
    
    # Обновляем превью если карточка готова — удаляем все и создаём новые
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")
    
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
    client_key_edited: str,
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

    # Обновляем превью если карточка готова — удаляем все и создаём новые
    from models.Card import CardStatus
    if card.status == CardStatus.ready:
        try:
            await delete_and_recreate_all_completes(card)
        except Exception as e:
            logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")


async def delete_and_recreate_all_completes(card: Card):
    """Helper: удалить все существующие превью для карточки и создать новые для всех клиентов."""
    try:
        async with session_factory() as s:
            # получаем все связанные сообщения и удаляем их
            complete_messages = await card.get_complete_preview_messages(session=s)
            if complete_messages:
                try:
                    info_ids = [m.message_id for m in complete_messages if m.message_type == 'complete_info']
                    post_ids = [m.message_id for m in complete_messages if m.message_type == 'complete_preview']
                    await delete_all_complete_previews(
                        info_ids=info_ids or None,
                        post_ids=post_ids or None
                    )
                except Exception as e:
                    logger.error(f"Ошибка удаления старых превью карточки {card.card_id}: {e}")

            clients = card.clients or []
            for client_key in clients:
                try:
                    await send_complete_preview(str(card.card_id), client_key, session=s)
                except Exception as e:
                    logger.error(f"Ошибка отправки превью карточки {card.card_id} (клиент {client_key}): {e}")

            await s.commit()
    except Exception as e:
        logger.error(f"Ошибка пересоздания превью карточки {card.card_id}: {e}")