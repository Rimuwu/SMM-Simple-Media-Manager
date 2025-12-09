from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID as _UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.connection import session_factory
from global_modules.classes.enums import CardType, ChangeType, UserRole
from global_modules.timezone import now_naive as moscow_now
from modules.kaiten import kaiten
from modules.properties import multi_properties
from global_modules.json_get import open_settings, open_properties
from models.Card import Card, CardStatus
from models.User import User
from modules.calendar import create_calendar_event, delete_calendar_event, update_calendar_event
from modules.scheduler import reschedule_post_tasks, schedule_card_notifications, cancel_card_tasks, reschedule_card_notifications, schedule_post_tasks
from modules.constants import (
    KaitenBoardNames, PropertyNames, 
    SceneNames, Messages
)
from modules.card_service import (
    notify_executor, get_kaiten_user_name, add_kaiten_comment, 
    update_kaiten_card_field, increment_reviewers_tasks, increment_customer_tasks
)
from modules.executors_client import (
    send_forum_message, update_forum_message, delete_forum_message, delete_forum_message_by_id,
    send_complete_preview, update_complete_preview, delete_complete_preview, delete_all_complete_previews,
    close_user_scene, update_task_scenes, close_card_related_scenes,
    notify_user, notify_users
)
from modules.logs import brain_logger as logger


# Создаём роутер
router = APIRouter(prefix='/card')
settings = open_settings() or {}

BOARD_ID = settings['space']['boards'][KaitenBoardNames.QUEUE]['id']
COLUMN_ID = settings['space']['boards'][KaitenBoardNames.QUEUE]['columns'][0]['id']

# Модель данных для создания карты
class CardCreate(BaseModel):
    title: str
    description: str
    deadline: Optional[str]  # ISO 8601 format (due_date)
    send_time: Optional[str] = None  # ISO 8601 format (due_date_time)

    executor_id: Optional[str] = None # ID исполнителя в базе данных
    customer_id: Optional[str] = None # ID заказчика в базе данных

    # properties
    channels: Optional[list[str]] = None  # Список каналов для публикации
    need_check: bool = True # Нужно ли проверять перед публикацией
    image_prompt: Optional[str] = None  # Промпт задачи для картинки
    tags: Optional[list[str]] = None  # Теги для карты
    type_id: CardType  # Тип задания


@router.post("/create")
async def create_card(card_data: CardCreate):
    logger.info(f"Запрос на создание карточки: {card_data.title}, Дедлайн: {card_data.deadline}, Исполнитель: {card_data.executor_id}")

    # Преобразовываем текстомвые ключи в id свойств
    channels = []
    properties_data = open_properties()
    if card_data.channels:
        for channel in card_data.channels:
            if channel.isdigit():
                channels.append(int(channel))
            else:
                channels.append(
                    properties_data[PropertyNames.CHANNELS]['values'][channel]['id']
            )

    tags = []
    if card_data.tags:
        for tag in card_data.tags:
            if tag.isdigit():
                tags.append(int(tag))
            else:
                tags.append(
                    properties_data[PropertyNames.TAGS]['values'][tag]['id']
                )

    card_type = settings['card_types'][card_data.type_id]['id']

    properties = multi_properties(
        channels=channels,
        editor_check=card_data.need_check,
        image_prompt=card_data.image_prompt,
        tags=tags
    )

    try:
        async with kaiten as client:

            res = await client.create_card(
                card_data.title,
                COLUMN_ID,
                card_data.description,
                BOARD_ID,
                due_date=card_data.deadline,
                due_date_time_present=True,
                properties=properties,
                type_id=card_type,
                position=1
            )

            card_id = res.id

            executor_ = await User.get_by_key('user_id', card_data.executor_id)
            customer_ = await User.get_by_key('user_id', card_data.customer_id)

            if card_id:
                try:
                    kaiten_card = await client.get_card(card_id)
                    members = await kaiten_card.get_members()
                    for member in members:
                        await client.remove_card_member(
                            card_id,
                            member.user_id
                        )
                except Exception as e:
                    logger.error(
                        f"Ошибка при получении/очистке членов карточки Kaiten: {e}"
                        )

                try:
                    if executor_ and kaiten_card and executor_.tasker_id:
                        await kaiten_card.add_member(executor_.tasker_id)
                except Exception as e:
                    logger.error(
                        f"Ошибка при добавлении исполнителя в карточку Kaiten: {e}"
                        )

                try:
                    if customer_ and kaiten_card and customer_.tasker_id:
                        await kaiten_card.add_member(customer_.tasker_id)
                except Exception as e:
                    logger.error(
                        f"Ошибка при добавлении заказчика в карточку Kaiten: {e}"
                        )

    except Exception as e:
        logger.error(f"Ошибка при создании карточки в Kaiten: {e}")
        card_id = 0

    card = await Card.create(
        name=card_data.title,
        description=card_data.description,
        task_id=card_id,
        clients=card_data.channels,
        tags=card_data.tags,
        deadline=datetime.fromisoformat(
            card_data.deadline) if card_data.deadline else None,
        send_time=datetime.fromisoformat(
            card_data.send_time) if card_data.send_time else None,
        image_prompt=card_data.image_prompt,
        customer_id=card_data.customer_id,
        executor_id=card_data.executor_id,
        need_check=card_data.need_check
    )

    logger.info(f"Карточка создана в БД: {card.card_id} (Kaiten ID: {card_id})")

    # Увеличиваем счётчик созданных задач у заказчика
    await increment_customer_tasks(card_data.customer_id)

    if card_data.type_id == CardType.public:
        message_id, error = await send_forum_message(str(card.card_id))
        if error:
            print(f"Error in forum send: {error}")
        if message_id:
            await card.update(forum_message_id=message_id)

    try:
        deadline_datetime = datetime.fromisoformat(card_data.deadline) if card_data.deadline else None

        # Добавляем ссылку в описание
        calendar_description = f"{card_data.description}"

        data = await create_calendar_event(
            card_data.title,
            calendar_description,
            deadline_datetime,
            all_day=True,
            color_id='7'
        )

        data = data.get('response', {}).get('data', {})
        calendar_id = data.get('id')
        if calendar_id:
            await card.refresh()
            await card.update(calendar_id=calendar_id)

    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return {'error': e.__str__()}

    # Отправляем уведомление исполнителю при создании личной задачи
    if card_data.type_id == CardType.private and card_data.executor_id:
        deadline_str = ""
        if card_data.deadline:
            try:
                deadline_dt = datetime.fromisoformat(card_data.deadline)
                deadline_str = f"\n⏰ Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')}"
            except Exception: pass

        message_text = f"{Messages.NEW_TASK}\n\n📝 {card_data.title}{deadline_str}\n\n{card_data.description}"
        await notify_executor(card_data.executor_id, message_text)

    if card_data.deadline:
        try:
            async with session_factory() as session:
                await card.refresh()
                await schedule_card_notifications(session, card)
        except Exception as e:
            print(f"Error scheduling card notifications: {e}")

    return {"card_id": str(card.card_id)}

@router.get("/get")
async def get(task_id: Optional[str] = None, 
              card_id: Optional[str] = None, 
              status: Optional[CardStatus] = None,
              customer_id: Optional[str] = None,
              executor_id: Optional[str] = None,
              need_check: Optional[bool] = None,
              forum_message_id: Optional[int] = None
              ):
    # Используем явный запрос с eager loading для связанных объектов
    async with session_factory() as session:
        stmt = select(Card).options(selectinload(Card.executor))
        
        # Применяем фильтры
        if task_id:
            stmt = stmt.where(Card.task_id == int(task_id))
        if card_id:
            stmt = stmt.where(Card.card_id == card_id)
        if status:
            stmt = stmt.where(Card.status == status)
        if customer_id:
            stmt = stmt.where(Card.customer_id == customer_id)
        if executor_id:
            stmt = stmt.where(Card.executor_id == executor_id)
        if need_check:
            stmt = stmt.where(Card.need_check == need_check)
        if forum_message_id:
            stmt = stmt.where(Card.forum_message_id == forum_message_id)
        
        result_db = await session.execute(stmt)
        cards = result_db.scalars().all()
        
        if not cards:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Получаем список пользователей из Kaiten один раз
        kaiten_users = {}
        try:
            async with kaiten as client:
                users = await client.get_company_users(only_virtual=True)
                kaiten_users = {u['id']: u['full_name'] for u in users}
        except Exception as e:
            print(f"Error getting Kaiten users: {e}")
        
        # Конвертируем карточки в словари
        result = []
        for card in cards:
            card_dict = card.to_dict()
            
            # Добавляем информацию об исполнителе
            if card.executor:
                kaiten_name = kaiten_users.get(card.executor.tasker_id) if card.executor.tasker_id else None
                
                card_dict['executor'] = {
                    'user_id': str(card.executor.user_id),
                    'telegram_id': card.executor.telegram_id,
                    'tasker_id': card.executor.tasker_id,
                    'full_name': kaiten_name or f"@{card.executor.telegram_id}"
                }
            else:
                card_dict['executor'] = None
            
            result.append(card_dict)
        
        return result

class CardUpdate(BaseModel):
    card_id: str
    name: Optional[str] = None  # Название карточки
    description: Optional[str] = None  # Описание карточки
    status: Optional[CardStatus] = None
    executor_id: Optional[str] = None
    customer_id: Optional[str] = None
    need_check: Optional[bool] = None
    need_send: Optional[bool] = None  # Нужно ли отправлять в каналы
    forum_message_id: Optional[int] = None
    content: Optional[str] = None
    clients: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    deadline: Optional[str] = None  # ISO 8601 format
    send_time: Optional[str] = None  # ISO 8601 format
    image_prompt: Optional[str] = None
    prompt_sended: Optional[bool] = None
    prompt_message: Optional[int] = None  # ID сообщения дизайнерам
    calendar_id: Optional[str] = None
    post_images: Optional[list[str]] = None  # Список имён файлов из Kaiten для публикации
    notify_executor: Optional[bool] = False  # Отправить уведомление исполнителю
    change_type: Optional[str] = None  # Тип изменения
    old_value: Optional[str] = None  # Старое значение
    new_value: Optional[str] = None  # Новое значение
    author_id: Optional[str] = None  # ID пользователя, который вносит изменения

@router.post("/update")
async def update_card(card_data: CardUpdate):

    card = await Card.get_by_key('card_id', card_data.card_id)
    if not card:
        logger.warning(f"Попытка обновления несуществующей карточки: {card_data.card_id}")
        raise HTTPException(
            status_code=404, detail="Card not found")

    data = card_data.model_dump(exclude={'card_id'})
    data = {k: v for k, v in data.items() if v is not None}

    # Логируем ключи, которые меняются
    logger.info(f"Обновление карточки {card.card_id}: {data}")

    # Преобразуем deadline в datetime
    if 'deadline' in data and isinstance(data['deadline'], str):
        try:
            data['deadline'] = datetime.fromisoformat(data['deadline'])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for deadline")

    # Преобразуем send_time
    if 'send_time' in data:
        if data['send_time'] == 'reset':
            data['send_time'] = None
        elif isinstance(data['send_time'], str):
            try:
                data['send_time'] = datetime.fromisoformat(data['send_time'])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for send_time")

    # Преобразуем UUID поля
    for key in ['executor_id', 'customer_id']:
        if key in data and isinstance(data[key], str):
            try:
                data[key] = _UUID(data[key])
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid UUID format for {key}")

    # Флаг для отслеживания, было ли сообщение форума уже обновлено при смене статуса
    forum_already_updated = False

    if 'status' in data and data['status'] != card.status:
        logger.info(f"Изменение статуса карточки {card.card_id}: {card.status} -> {data['status']}")

        # Если статус изменился на review (ждет проверки)
        if data['status'] == CardStatus.review:
            forum_already_updated = True  # Помечаем что форум обновим здесь
            
            # Перемещаем карточку в Kaiten в колонку "На проверке"
            if card.task_id and card.task_id != 0:
                try:
                    board_id = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['id']
                    column_id = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['columns'][1]['id']
                    async with kaiten as client:
                        await client.update_card(
                            card.task_id, board_id=board_id, column_id=column_id)
                        await client.add_comment(card.task_id, "🔍 Задача отправлена на проверку")
                except Exception as e:
                    print(f"Error moving card to review in Kaiten: {e}")

            # Удаляем старое сообщение с форума
            if card.forum_message_id:
                if await delete_forum_message(str(card.card_id)):
                    await card.update(forum_message_id=None)
            
            # Создаём новое сообщение на форуме со статусом review
            await card.refresh()
            message_id, _ = await update_forum_message(str(card.card_id), CardStatus.review.value)
            if message_id:
                await card.update(forum_message_id=message_id)
            
            # Уведомляем админов и редакторов
            recipients = []
            admins = await User.filter_by(role=UserRole.admin)
            editors = await User.filter_by(role=UserRole.editor)
            if admins: recipients.extend(admins)
            if editors: recipients.extend(editors)
            recipients = list({u.user_id: u for u in recipients}.values())
            
            msg = f"🔔 Задача требует проверки!\n\n📝 {card.name}\n\nПожалуйста, проверьте задачу и измените статус."
            await notify_users(recipients, msg)

        elif data['status'] == CardStatus.edited:
            forum_already_updated = True  # Помечаем что форум обновим здесь
            
            # Если статус меняется на edited (в работе), удаляем запланированные задачи публикации и превью
            if card.status == CardStatus.ready:
                try:
                    async with session_factory() as session:
                        await cancel_card_tasks(session, str(card.card_id))
                        print(f"Cancelled tasks for card {card.card_id} due to status change to edited")
                        
                        # Восстанавливаем напоминания (дедлайны и т.д.), так как cancel_card_tasks удаляет всё
                        await card.refresh()
                        await schedule_card_notifications(session, card)
                        print(f"Restored notifications for card {card.card_id}")
                except Exception as e:
                    print(f"Error canceling tasks: {e}")
                
                # Удаляем превью из complete_topic
                try:
                    complete_message_ids = card.complete_message_id or {}
                    await delete_all_complete_previews(complete_message_ids)
                    await card.update(complete_message_id={})
                    print(f"Deleted complete previews for card {card.card_id}")
                except Exception as e:
                    print(f"Error deleting complete previews: {e}")

            board_id = settings['space'][
                'boards'][KaitenBoardNames.IN_PROGRESS]['id']
            column_id = settings['space'][
                'boards'][KaitenBoardNames.IN_PROGRESS]['columns'][0]['id']

            if card.task_id != 0:
                async with kaiten as client:
                    await client.update_card(
                        card.task_id,
                        board_id=board_id,
                        column_id=column_id
                    )

                    await client.add_comment(
                        card.task_id,
                        Messages.TASK_TAKEN
                    )
            
            # Обновляем сцену исполнителя
            await update_task_scenes(str(card.card_id))
            
            # Сначала сохраняем executor_id в базу, чтобы форум показал исполнителя
            if 'executor_id' in data:
                await card.update(executor_id=data['executor_id'])
                await card.refresh()

            # Обновляем сообщение на форуме
            if card.forum_message_id:
                message_id, _ = await update_forum_message(str(card.card_id), CardStatus.edited.value)
                if message_id:
                    await card.update(forum_message_id=message_id)

        need_send = data.get('need_send', card.need_send)

        # Обработка изменения статуса на ready - создаем задачи публикации
        if data['status'] == CardStatus.ready:
            # Перемещаем карточку в Kaiten в колонку "Готово"
            if card.task_id and card.task_id != 0:
                try:
                    board_id = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['id']
                    column_id = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['columns'][2]['id']
                    async with kaiten as client:
                        await client.update_card(card.task_id, board_id=board_id, column_id=column_id)
                        await client.add_comment(card.task_id, "✅ Задача готова к публикации")
                except Exception as e:
                    print(f"Error moving card to ready in Kaiten: {e}")

            # Закрываем сцену исполнителя
            if card.executor_id:
                executor = await User.get_by_key('user_id', card.executor_id)
                if executor:
                    await close_user_scene(executor.telegram_id)

            # Планируем задачи публикации только если need_send = True
            await card.refresh()
            if need_send:
                try:
                    async with session_factory() as session:
                        await schedule_post_tasks(session, card)
                        print(f"Scheduled post tasks for card {card.card_id}")
                except Exception as e:
                    print(f"Error scheduling post tasks: {e}")
            else:
                # Если need_send=False, сразу меняем статус на sent и финализируем
                logger.info(
                    f"Карточка {card.card_id} не требует отправки (need_send=False), меняем статус на sent"
                    )
                await card.update(status=CardStatus.sent)
                data['status'] = CardStatus.sent  # Меняем статус на sent, если не нужно отправлять

            # Обновляем сообщение на форуме со статусом ready
            if need_send:
                await card.refresh()
                message_id, _ = await update_forum_message(str(card.card_id), CardStatus.ready.value)
                if message_id:
                    await card.update(forum_message_id=message_id)
                forum_already_updated = True

            # Отправляем превью постов в complete_topic для каждого клиента
            try:
                await card.refresh()
                complete_message_ids = card.complete_message_id or {}
                
                clients = card.clients or []
                for client_key in clients:
                    preview_res = await send_complete_preview(str(card.card_id), client_key)
                    if preview_res.get("success"):
                        complete_message_ids[client_key] = {
                            "post_id": preview_res.get("post_id"),
                            "post_ids": preview_res.get("post_ids", []),
                            "info_id": preview_res.get("info_id")
                        }
                
                if complete_message_ids:
                    await card.update(complete_message_id=complete_message_ids)
                    print(f"Sent complete previews for card {card.card_id}: {complete_message_ids}")
            except Exception as e:
                print(f"Error sending complete previews: {e}")

            # Уведомляем заказчика о готовности задачи
            if card.customer_id:
                customer = await User.get_by_key('user_id', card.customer_id)
                if customer:
                    deadline_str = card.deadline.strftime('%d.%m.%Y %H:%M') if card.deadline else 'Не установлен'
                    message_text = (
                        f"✅ Задача готова!\n\n"
                        f"📝 Название: {card.name}\n"
                        f"⏰ Дедлайн: {deadline_str}\n\n"
                        f"Задача готова к публикации."
                    )
                    await notify_user(customer.telegram_id, message_text)
                    print(f"Notified customer {customer.telegram_id} about ready card {card.card_id}")

        # Обработка изменения статуса на sent (отправлено)
        if data['status'] == CardStatus.sent:
            # Перемещаем карточку в Kaiten в колонку "Готово"
            try:
                board_id = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['id']
                # ID колонки "Готово" - 3-я колонка (индекс 2)
                column_id = settings['space']['boards'][KaitenBoardNames.IN_PROGRESS]['columns'][2]['id']
                
                if card.task_id != 0:
                    async with kaiten as client:
                        await client.update_card(
                            card.task_id,
                            board_id=board_id,
                            column_id=column_id
                        )
                        await client.add_comment(
                            card.task_id,
                            "🚀 Задача выполнена и отправлена!"
                        )
            except Exception as e:
                print(f"Error moving card in Kaiten: {e}")

            # Удаляем сообщение с форума
            if card.forum_message_id:
                if await delete_forum_message(str(card.card_id)):
                    await card.update(forum_message_id=None)

            # Увеличиваем счетчик выполненных задач у исполнителя
            if card.executor_id:
                try:
                    executor = await User.get_by_key('user_id', card.executor_id)
                    if executor:
                        await executor.update(
                            tasks=executor.tasks + 1,
                            task_per_month=executor.task_per_month + 1,
                            task_per_year=executor.task_per_year + 1
                        )
                        print(f"Incremented task count for user {executor.user_id}")
                except Exception as e:
                    print(f"Error incrementing task count: {e}")

            await increment_reviewers_tasks(card)

            # Закрываем все сцены, связанные с этой задачей
            await close_card_related_scenes(str(card.card_id))
            
            # Создаём задачу на удаление карточки через 2 дня
            try:
                from models.ScheduledTask import ScheduledTask
                from uuid import UUID as PyUUID

                delete_at = moscow_now() + timedelta(days=0.5)
                card_uuid = card.card_id if isinstance(card.card_id, PyUUID) else PyUUID(str(card.card_id))

                async with session_factory() as session:
                    task = ScheduledTask(
                        card_id=card_uuid,
                        function_path="modules.notifications.delete_sent_card",
                        execute_at=delete_at,
                        arguments={"card_id": str(card.card_id)}
                    )
                    session.add(task)
                    await session.commit()
                    logger.info(f"Создана задача удаления карточки {card.card_id} на {delete_at}")
            except Exception as e:
                logger.error(f"Ошибка создания задачи удаления: {e}")

    if 'executor_id' in data:
        logger.info(f"Изменение исполнителя карточки {card.card_id}: {card.executor_id} -> {data['executor_id']}")
        
        await card.update(executor_id=data['executor_id'])

        user = await User.get_by_key(
            'user_id', data['executor_id']
        )
        if user and card.task_id != 0:
            tasker_id = user.tasker_id
            if tasker_id:

                async with kaiten as client:
                    
                    card_k = await client.get_card(card.task_id)
                    if card_k:
                        members = await card_k.get_members()
                        member_ids = [m['id'] for m in members]
                        
                        for member in member_ids:
                            if member not in [
                                card.customer_id, card.executor_id
                            ]:
                                await client.remove_card_member(
                                    card.task_id,
                                    member
                                ) 
                        if tasker_id not in member_ids:
                            await client.add_card_member(
                                card.task_id,
                                tasker_id
                            )

    # Обработка изменения каналов (clients)
    if 'clients' in data and card.task_id and card.task_id != 0:
        props = open_properties()
        new_channels = []
        if data['clients']:
            for channel in data['clients']:
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
                    properties=multi_properties(
                        channels=new_channels
                    )
                )
        except Exception as e:
            print(f"Error updating channels in Kaiten: {e}")

    # Обработка изменения тегов (tags)
    if 'tags' in data and card.task_id and card.task_id != 0:
        props = open_properties()
        new_tags = []
        if data['tags']:
            for tag in data['tags']:
                if str(tag).isdigit():
                    new_tags.append(int(tag))
                else:
                    new_tags.append(
                        props[PropertyNames.TAGS]['values'][tag]['id']
                    )

        try:
            async with kaiten as client:
                await client.update_card(
                    card.task_id,
                    properties=multi_properties(
                        tags=new_tags
                    )
                )
        except Exception as e:
            print(f"Error updating tags in Kaiten: {e}")

    # Обработка изменения name (названия)
    if 'name' in data and card.task_id and card.task_id != 0:
        comment = f"✏️ Название изменено на: {data['name']}"
        if card_data.old_value and card_data.new_value:
            comment = f"✏️ Название изменено:\n{card_data.old_value} → {card_data.new_value}"
        
        await update_kaiten_card_field(card.task_id, 'title', data['name'], comment)
    
    # Обработка изменения description (описания)
    if 'description' in data and card.task_id and card.task_id != 0:
        comment = f"📝 Описание обновлено:\n{data['description'][:200]}"
        if len(data['description']) > 200:
            comment += "..."
        
        await update_kaiten_card_field(card.task_id, 'description', data['description'], comment)
    
    # Обработка изменения deadline
    deadline_changed = False
    if 'deadline' in data and card.task_id and card.task_id != 0:
        logger.info(f"Изменение дедлайна карточки {card.card_id}: {data['deadline']}")
        deadline_changed = True
        comment = Messages.DEADLINE_CHANGED
        if card_data.old_value and card_data.new_value:
            try:
                old_dt = datetime.fromisoformat(card_data.old_value)
                new_dt = datetime.fromisoformat(card_data.new_value)
                comment = f"⏰ Дедлайн изменен: {old_dt.strftime('%d.%m.%Y %H:%M')} → {new_dt.strftime('%d.%m.%Y %H:%M')}"
            except:
                pass
        
        # Добавляем информацию об авторе изменения в комментарий Kaiten
        if card_data.author_id:
            try:
                author = await User.get_by_key('user_id', card_data.author_id)
                if author:
                    author_name = await get_kaiten_user_name(author)
                    comment += f"\n👤 Изменил: {author_name}"
            except Exception as e:
                logger.error(f"Ошибка получения имени автора для комментария: {e}")
        
        await update_kaiten_card_field(
            card.task_id, 
            'due_date', 
            data['deadline'].strftime('%Y-%m-%d'), 
            comment
        )
        
        # Обновляем событие в календаре если есть calendar_id
        if card.calendar_id:
            try:
                await update_calendar_event(
                    event_id=card.calendar_id,
                    start_time=data['deadline']
                )
                print(f"Calendar event {card.calendar_id} updated with new deadline")
            except Exception as e:
                print(f"Error updating calendar event: {e}")

    # Обработка изменения send_time - перепланируем задачи публикации
    send_time_changed = False
    if 'send_time' in data:
        # Преобразуем send_time в datetime если это строка
        if isinstance(data['send_time'], str):
            try:
                data['send_time'] = datetime.fromisoformat(data['send_time'])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for send_time")
        
        # Проверяем, действительно ли изменилось время
        if data['send_time'] != card.send_time:
            send_time_changed = True

    await card.update(**data)
    
    # Перепланируем задачи при изменении дедлайна
    if deadline_changed:
        try:
            async with session_factory() as session:
                await card.refresh()
                await reschedule_card_notifications(session, card)
        except Exception as e:
            print(f"Error rescheduling card notifications: {e}")
    
    # Перепланируем задачи публикации при изменении send_time или clients
    clients_changed = 'clients' in data
    if send_time_changed or clients_changed:
        try:
            async with session_factory() as session:
                await card.refresh()
                await reschedule_post_tasks(session, card)
                print(f"Rescheduled post tasks for card {card.card_id} (send_time={send_time_changed}, clients={clients_changed})")
        except Exception as e:
            print(f"Error rescheduling post tasks: {e}")
    
    # Обновляем сообщение на форуме если есть forum_message_id и изменились важные данные
    # Но только если форум не был уже обновлён при смене статуса
    if card.forum_message_id and not forum_already_updated:
        # Список полей, при изменении которых нужно обновить сообщение на форуме
        # Не включаем content - он не отображается на форуме
        # Не включаем status - он обрабатывается отдельно выше
        forum_update_fields = ['executor_id', 'deadline', 'name', 'description']
        should_update_forum = any(field in data for field in forum_update_fields)
        
        if should_update_forum:
            # Определяем статус для отправки
            forum_status = card.status.value if hasattr(card.status, 'value') else str(card.status)
            message_id, error = await update_forum_message(str(card.card_id), forum_status)
            if error:
                print(f"Failed to update forum message: {error}")
    
    # Обновляем превью в complete_topic если изменились поля, влияющие на пост
    # и статус карточки - ready (пост ожидает публикации)
    await card.refresh()
    complete_update_fields = ['content', 'tags', 'post_images', 'clients', 'send_time']
    should_update_complete = any(field in data for field in complete_update_fields)
    
    if should_update_complete and card.status == CardStatus.ready and card.complete_message_id:
        try:
            complete_message_ids = card.complete_message_id or {}
            clients = card.clients or []
            
            # Удаляем превью для клиентов, которых больше нет
            for client_key in list(complete_message_ids.keys()):
                if client_key not in clients:
                    msg_data = complete_message_ids.pop(client_key)
                    # Поддерживаем как новый формат (dict), так и старый (int)
                    if isinstance(msg_data, dict):
                        await delete_complete_preview(
                            post_id=msg_data.get("post_id"),
                            post_ids=msg_data.get("post_ids"),
                            info_id=msg_data.get("info_id")
                        )
                    else:
                        await delete_complete_preview(post_id=msg_data)
            
            # Обновляем или добавляем превью для текущих клиентов
            for client_key in clients:
                if client_key in complete_message_ids:
                    msg_data = complete_message_ids[client_key]
                    # Поддерживаем как новый формат (dict), так и старый (int)
                    if isinstance(msg_data, dict):
                        post_id = msg_data.get("post_id")
                        post_ids = msg_data.get("post_ids", [])
                        info_id = msg_data.get("info_id")
                    else:
                        post_id = msg_data
                        post_ids = [msg_data] if msg_data else []
                        info_id = None
                    
                    # Обновляем существующее превью
                    update_res = await update_complete_preview(
                        str(card.card_id),
                        client_key,
                        post_id,
                        post_ids,
                        info_id
                    )
                    # Если вернулись новые ID (было пересоздано), обновляем
                    if update_res.get("post_id"):
                        complete_message_ids[client_key] = {
                            "post_id": update_res.get("post_id"),
                            "post_ids": update_res.get("post_ids", []),
                            "info_id": update_res.get("info_id")
                        }
                else:
                    # Создаём новое превью для нового клиента
                    preview_res = await send_complete_preview(str(card.card_id), client_key)
                    if preview_res.get("success"):
                        complete_message_ids[client_key] = {
                            "post_id": preview_res.get("post_id"),
                            "post_ids": preview_res.get("post_ids", []),
                            "info_id": preview_res.get("info_id")
                        }
            
            await card.update(complete_message_id=complete_message_ids)
            print(f"Updated complete previews for card {card.card_id}: {complete_message_ids}")
        except Exception as e:
            print(f"Error updating complete previews: {e}")
    
    # Отправляем уведомление исполнителю
    if card_data.notify_executor and card.executor_id:
        change_messages = {
            ChangeType.DEADLINE.value: '⏰ Изменен дедлайн',
            ChangeType.COMMENT.value: '💬 Добавлен комментарий',
            ChangeType.NAME.value: '✏️ Изменено название',
            ChangeType.DESCRIPTION.value: '📝 Изменено описание'
        }
        message_text = change_messages.get(card_data.change_type or '', Messages.CHANGE_NOTIFICATION.value)
        
        # Добавляем информацию об авторе изменений
        if card_data.author_id:
            try:
                author = await User.get_by_key('user_id', card_data.author_id)
                if author:
                    author_name = await get_kaiten_user_name(author)
                    message_text += f"\n👤 Изменил: {author_name}"
            except Exception as e:
                logger.error(f"Ошибка получения имени автора: {e}")
        
        message_text += f"\n\n📝 Задача: {card.name}"
        
        if card_data.change_type == ChangeType.DEADLINE.value and card_data.new_value:
            try:
                new_dt = datetime.fromisoformat(card_data.new_value)
                message_text += f"\n⏰ Новый дедлайн: {new_dt.strftime('%d.%m.%Y %H:%M')}"
            except:
                pass
        elif card_data.change_type == ChangeType.NAME.value and card_data.new_value:
            message_text += f"\n\nНовое название: {card_data.new_value}"
        elif card_data.change_type == ChangeType.DESCRIPTION.value and card_data.new_value:
            # Обрезаем длинное описание
            description_preview = card_data.new_value[:200] + "..." if len(card_data.new_value) > 200 else card_data.new_value
            message_text += f"\n\nНовое описание:\n{description_preview}"
        
        await notify_executor(str(card.executor_id), message_text)
    
    return card.to_dict()

@router.get('/delete-executor/{card_id}')
async def delete_executor(card_id: str):
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        raise HTTPException(
            status_code=404, detail="Card not found")

    executor_uuid = card.executor_id
    await card.update(executor_id=None)

    user = await User.get_by_id(executor_uuid)
    if user:

        if card.executor_id != card.customer_id:
            await close_user_scene(user.telegram_id)

            if card.task_id and user.tasker_id:
                async with kaiten as client:
                    await client.remove_card_member(card.task_id, 
                                                    user.tasker_id)

    return {"detail": "Executor removed successfully"}


class ReturnToForumRequest(BaseModel):
    card_id: str


@router.post("/return-to-forum")
async def return_to_forum(request: ReturnToForumRequest):
    """
    Возвращает задачу на форум:
    - Убирает исполнителя
    - Меняет статус на pass_
    - Удаляет старое сообщение форума и создаёт новое
    - Удаляет complete_message_id
    - Отменяет все запланированные задачи
    """
    logger.info(f"Запрос на возврат карточки {request.card_id} на форум")
    card = await Card.get_by_key('card_id', request.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # 1. Отменяем все запланированные задачи
    try:
        async with session_factory() as session:
            await cancel_card_tasks(session, str(card.card_id))
            logger.info(f"Отменены запланированные задачи для карточки {card.card_id}")
    except Exception as e:
        logger.error(f"Ошибка отмены задач для карточки {card.card_id}: {e}")
    
    # 2. Удаляем complete_message (превью готовых постов)
    if card.complete_message_id:
        await delete_all_complete_previews(card.complete_message_id)
        logger.info(f"Удалены превью готовых постов для карточки {card.card_id}")
    
    # 3. Удаляем старое сообщение форума
    if card.forum_message_id:
        if await delete_forum_message(str(card.card_id)):
            logger.info(f"Удалено старое сообщение форума для карточки {card.card_id}")
        else:
            logger.error(f"Ошибка удаления старого сообщения форума для карточки {card.card_id}")
    
    # 4. Обновляем карточку: сбрасываем исполнителя, статус, complete_message_id, forum_message_id
    await card.update(
        executor_id=None,
        status=CardStatus.pass_,
        complete_message_id={},
        forum_message_id=None
    )
    
    # 5. Обновляем карточку в Kaiten (убираем исполнителя, перемещаем в очередь)
    if card.task_id and card.task_id != 0:
        try:
            board_id = settings['space']['boards'][KaitenBoardNames.QUEUE]['id']
            column_id = settings['space']['boards'][KaitenBoardNames.QUEUE]['columns'][0]['id']
            
            async with kaiten as client:
                await client.update_card(
                    card.task_id,
                    executor_id=None,
                    board_id=board_id,
                    column_id=column_id
                )
                await client.add_comment(card.task_id, "📤 Задача возвращена на форум")
            logger.info(f"Карточка {card.card_id} перемещена в очередь в Kaiten")
        except Exception as e:
            logger.error(f"Ошибка обновления карточки в Kaiten: {e}")
    
    # 6. Создаём новое сообщение на форуме
    message_id, error = await send_forum_message(str(card.card_id))
    if message_id:
        await card.update(forum_message_id=message_id)
        logger.info(f"Создано новое сообщение форума для карточки {card.card_id}: {message_id}")
    else:
        logger.error(f"Ошибка создания сообщения форума: {error}")
    
    # 7. Закрываем сцены редактирования для этой задачи
    await update_task_scenes(str(card.card_id))
    
    logger.info(f"Карточка {card.card_id} успешно возвращена на форум")
    return {"detail": "Card returned to forum successfully"}


@router.delete("/delete/{card_id}")
async def delete_card(card_id: str):
    logger.info(f"Запрос на удаление карточки {card_id}")
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        logger.warning(f"Попытка удаления несуществующей карточки: {card_id}")
        raise HTTPException(
            status_code=404, detail="Card not found")

    # Удаляем все запланированные задачи для карточки
    try:
        async with session_factory() as session:
            await cancel_card_tasks(session, card_id)
    except Exception as e:
        logger.error(f"Ошибка при отмене задач карточки {card_id}: {e}")

    await card.delete()

    if card.status != CardStatus.sent and card.task_id:
        async with kaiten as client:
            try:
                await client.delete_card(card.task_id)
            except Exception as e:
                logger.error(f"Ошибка удаления карточки {card_id} из Kaiten: {e}")
                return {"detail": f"Card deleted from DB, but failed to delete from Kaiten: {e}"}

    if card.status != CardStatus.sent:
        try:
            if card.calendar_id:
                await delete_calendar_event(card.calendar_id)
        except Exception as e:
            logger.error(f"Ошибка удаления события календаря для карточки {card_id}: {e}")
            return {"detail": f"Card deleted from DB, but failed to delete from Calendar: {e}"}

    if card.forum_message_id:
        if not await delete_forum_message_by_id(card.forum_message_id):
            logger.error(f"Ошибка удаления сообщения форума для карточки {card_id}")
            return {"detail": "Card deleted from DB, but failed to delete forum message"}

    logger.info(f"Карточка {card_id} успешно удалена")
    return {"detail": "Card deleted successfully"}

class CommentAdd(BaseModel):
    card_id: str
    content: str
    author: str  # user_id автора комментария

@router.post("/add-comment")
async def add_comment(note_data: CommentAdd):
    """Добавить комментарий к карточке (обычный комментарий от заказчика)"""
    logger.info(f"Добавление комментария к карточке {note_data.card_id} от {note_data.author}")
    card = await Card.get_by_key('card_id', note_data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Сохраняем комментарий в editor_notes с пометкой is_customer
    editor_notes = card.editor_notes or []
    new_note = {
        "content": note_data.content,
        "author": note_data.author,
        "is_customer": True,
        "created_at": datetime.now().isoformat()
    }
    editor_notes.append(new_note)
    await card.update(editor_notes=editor_notes)
    
    # Добавляем комментарий в Kaiten
    if card.task_id and card.task_id != 0:
        try:
            # Получаем имя автора
            author = await User.get_by_key('user_id', note_data.author)
            author_name = "Unknown"
            if author:
                author_name = await get_kaiten_user_name(author)
            
            comment_text = f"💬 Заказчик ({author_name}): {note_data.content}"
            
            await add_kaiten_comment(card.task_id, comment_text)
        except Exception as e:
            logger.error(f"Ошибка добавления комментария в Kaiten: {e}")
    
    # Отправляем уведомление исполнителю
    if card.executor_id:
        message_text = f"{Messages.NEW_COMMENT}\n\n📝 {card.name}\n\n{note_data.content}"
        await notify_executor(
            str(card.executor_id), 
            message_text, 
            task_id=str(card.card_id), 
            skip_if_page="editor-notes"
        )
    
    return {
        "detail": "Comment added successfully"
    }

class EditorNoteAdd(BaseModel):
    card_id: str
    content: str
    author: str  # user_id автора комментария

@router.post("/add-editor-note")
async def add_editor_note(note_data: EditorNoteAdd):
    """Добавить комментарий редактора к карточке"""
    logger.info(f"Добавление комментария редактора к карточке {note_data.card_id} от {note_data.author}")
    card = await Card.get_by_key('card_id', note_data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Получаем текущий список комментариев
    editor_notes = card.editor_notes or []
    
    # Добавляем новый комментарий
    new_note = {
        "content": note_data.content,
        "author": note_data.author,
        "created_at": datetime.now().isoformat()
    }
    editor_notes.append(new_note)
    
    # Обновляем карточку
    await card.update(editor_notes=editor_notes)
    
    # Добавляем комментарий в Kaiten если есть task_id
    if card.task_id and card.task_id != 0:
        try:
            # Получаем информацию о пользователе
            user = await User.get_by_key('user_id', note_data.author)
            author_name = f"User {note_data.author}"
            if user:
                author_name = await get_kaiten_user_name(user)
            
            comment_text = f"💬 Комментарий от {author_name}:\n{note_data.content}"
            await add_kaiten_comment(card.task_id, comment_text)
        except Exception as e:
            logger.error(f"Ошибка добавления комментария в Kaiten: {e}")
    
    # Обновляем все открытые сцены с этой карточкой
    await update_task_scenes(str(note_data.card_id), SceneNames.USER_TASK)
    
    # Отправляем уведомление исполнителю, если он не автор
    if card.executor_id and str(card.executor_id) != str(note_data.author):
        message_text = f"💬 Новый комментарий редактора\n\n📝 {card.name}\n\n{note_data.content}"
        await notify_executor(
            str(card.executor_id), 
            message_text, 
            task_id=str(card.card_id), 
            skip_if_page="editor-notes"
        )

    return {
        "detail": "Note added successfully",
        "note": new_note,
        "total_notes": len(editor_notes)
    }


class SendNowRequest(BaseModel):
    card_id: str

@router.post("/send-now")
async def send_now(request: SendNowRequest):
    """
    Отправить карточку немедленно.
    Обновляет время существующих задач на текущее (не удаляет и не создаёт новые).
    """
    logger.info(f"Запрос на немедленную отправку карточки {request.card_id}")
    
    card = await Card.get_by_key('card_id', request.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card.status != CardStatus.ready:
        raise HTTPException(status_code=400, detail="Card must be in ready status to send")
    
    from datetime import timedelta
    from global_modules.timezone import now_naive as moscow_now
    from modules.scheduler import update_post_tasks_time, schedule_post_tasks
    
    # Устанавливаем время отправки на 5 секунд вперёд
    now = moscow_now()
    send_time = now + timedelta(seconds=5)
    
    await card.update(send_time=send_time)
    logger.info(f"Время отправки карточки {card.card_id} установлено на {send_time}")
    
    # Пробуем обновить время существующих задач
    try:
        async with session_factory() as session:
            await card.refresh()
            updated_count = await update_post_tasks_time(session, card, send_time)
            
            # Если задач не было (например, первый раз нажали), создаём новые
            if updated_count == 0:
                logger.info(f"Задач для обновления не найдено, создаём новые для карточки {card.card_id}")
                await schedule_post_tasks(session, card)
            else:
                logger.info(f"Обновлено {updated_count} задач публикации для карточки {card.card_id}")
    except Exception as e:
        logger.error(f"Ошибка обновления задач публикации: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating tasks: {e}")
    
    return {
        "detail": "Card scheduled for immediate sending",
        "send_time": send_time.isoformat()
    }


class NotifyExecutorRequest(BaseModel):
    card_id: str
    message: str


@router.post("/notify-executor")
async def notify_executor_endpoint(data: NotifyExecutorRequest):
    """
    Отправляет уведомление исполнителю задачи.
    """
    card = await Card.get_by_key('card_id', data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if not card.executor_id:
        raise HTTPException(status_code=400, detail="Card has no executor")
    
    await notify_executor(str(card.executor_id), data.message, task_id=data.card_id)
    
    return {"detail": "Notification sent"}