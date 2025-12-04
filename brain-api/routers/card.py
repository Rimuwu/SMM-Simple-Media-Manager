from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID
from os import getenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.connection import session_factory
from global_modules.classes.enums import CardType, ChangeType, UserRole
from modules.kaiten import kaiten
from modules.properties import multi_properties
from modules.json_get import open_settings, open_properties
from models.Card import Card, CardStatus
from models.User import User
from modules.api_client import executors_api
from modules.calendar import create_calendar_event, delete_calendar_event, update_calendar_event
from modules.scheduler import reschedule_post_tasks, schedule_card_notifications, cancel_card_tasks, reschedule_card_notifications, schedule_post_tasks
from modules.constants import (
    KaitenBoardNames, PropertyNames, ApiEndpoints, 
    SceneNames, Messages
)
from modules.card_service import (
    notify_executor, get_kaiten_user_name, add_kaiten_comment, 
    update_kaiten_card_field
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
    editor_check: bool = True # Нужно ли проверять перед публикацией
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

    card_type = settings['card-types'][card_data.type_id]

    properties = multi_properties(
        channels=channels,
        editor_check=card_data.editor_check,
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
                position=1,
                executor_id=card_data.executor_id,
            )

            card_id = res.id
    except Exception as e:
        logger.error(f"Ошибка при создании карточки в Kaiten: {e}")
        card_id = 0

    card = await Card.create(
        name=card_data.title,
        description=card_data.description,
        task_id=card_id,
        clients=card_data.channels,
        tags=card_data.tags,
        deadline=datetime.fromisoformat(card_data.deadline) if card_data.deadline else None,
        send_time=datetime.fromisoformat(card_data.send_time) if card_data.send_time else None,
        image_prompt=card_data.image_prompt,
        customer_id=card_data.customer_id,
        executor_id=card_data.executor_id,
    )
    
    logger.info(f"Карточка создана в БД: {card.card_id} (Kaiten ID: {card_id})")

    if card_data.type_id == CardType.public:

        forum_res, status = await executors_api.post(
            ApiEndpoints.FORUM_SEND_MESSAGE,
                data={"card_id": str(card.card_id)}
        )

        error = forum_res.get('error')
        if error:
            print(f"Error in forum send: {error}")

        message_id = forum_res.get("message_id", None)
        if message_id:
            await card.update(forum_message_id=message_id)

    try:
        deadline_datetime = datetime.fromisoformat(card_data.deadline) if card_data.deadline else None

        # Формируем ссылку на задание в Telegram боте
        bot_username = getenv('BOT_USERNAME', 'your_bot')
        task_link = f"https://t.me/{bot_username}?start=task_{card.card_id}"
        
        # Добавляем ссылку в описание
        calendar_description = f"{card_data.description}\n\n📎 Ссылка на задание: {task_link}"

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
            except:
                pass
        
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
        if need_check is not None:
            stmt = stmt.where(Card.need_check == need_check)
        if forum_message_id is not None:
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
    forum_message_id: Optional[int] = None
    content: Optional[str] = None
    clients: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    deadline: Optional[str] = None  # ISO 8601 format
    send_time: Optional[str] = None  # ISO 8601 format
    image_prompt: Optional[str] = None
    prompt_sended: Optional[bool] = None
    calendar_id: Optional[str] = None
    post_images: Optional[list[str]] = None  # Список имён файлов из Kaiten для публикации
    notify_executor: Optional[bool] = False  # Отправить уведомление исполнителю
    change_type: Optional[str] = None  # Тип изменения
    old_value: Optional[str] = None  # Старое значение
    new_value: Optional[str] = None  # Новое значение

@router.post("/update")
async def update_card(card_data: CardUpdate):
    # print(card_data.__dict__)

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
                        await client.update_card(card.task_id, board_id=board_id, column_id=column_id)
                        await client.add_comment(card.task_id, "🔍 Задача отправлена на проверку")
                except Exception as e:
                    print(f"Error moving card to review in Kaiten: {e}")
            
            # Удаляем старое сообщение с форума
            if card.forum_message_id:
                try:
                    await executors_api.delete(ApiEndpoints.FORUM_DELETE_MESSAGE.value.format(card.card_id))
                    await card.update(forum_message_id=None)
                except Exception as e:
                    print(f"Error deleting forum message: {e}")
            
            # Создаём новое сообщение на форуме со статусом review
            try:
                await card.refresh()
                forum_res, _ = await executors_api.post(
                    ApiEndpoints.FORUM_UPDATE_MESSAGE,
                    data={"card_id": str(card.card_id), "status": CardStatus.review.value}
                )
                message_id = forum_res.get("message_id")
                if message_id:
                    await card.update(forum_message_id=message_id)
            except Exception as e:
                print(f"Error creating forum message for review: {e}")
            
            # Уведомляем админов и редакторов
            recipients = []
            admins = await User.filter_by(role=UserRole.admin)
            editors = await User.filter_by(role=UserRole.editor)
            if admins: recipients.extend(admins)
            if editors: recipients.extend(editors)
            recipients = list({u.user_id: u for u in recipients}.values())
            
            msg = f"🔔 Задача требует проверки!\n\n📝 {card.name}\n\nПожалуйста, проверьте задачу и измените статус."
            
            for recipient in recipients:
                try:
                    await executors_api.post(
                        ApiEndpoints.NOTIFY_USER,
                        data={"user_id": recipient.telegram_id, "message": msg}
                    )
                except Exception as e:
                    print(f"Error notifying recipient {recipient.telegram_id}: {e}")

        if data['status'] == CardStatus.edited:
            forum_already_updated = True  # Помечаем что форум обновим здесь
            
            # Если статус меняется на edited (в работе), удаляем запланированные задачи публикации (если были)
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
            try:
                await executors_api.post(ApiEndpoints.UPDATE_SCENES, data={
                    "scene_name": SceneNames.USER_TASK,
                    "data_key": "task_id",
                    "data_value": str(card.card_id)
                })
            except Exception as e:
                print(f"Error updating executor scene: {e}")
            
            # Обновляем сообщение на форуме
            try:
                await card.refresh()
                forum_res, _ = await executors_api.post(
                    ApiEndpoints.FORUM_UPDATE_MESSAGE,
                    data={"card_id": str(card.card_id), "status": CardStatus.edited.value}
                )
                message_id = forum_res.get("message_id")
                if message_id:
                    await card.update(forum_message_id=message_id)
            except Exception as e:
                print(f"Error updating forum message: {e}")

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
                try:
                    executor = await User.get_by_key('user_id', card.executor_id)
                    if executor:
                        await executors_api.post(f'/events/close_scene/{executor.telegram_id}')
                except Exception as e:
                    print(f"Error closing executor scene: {e}")
            
            # Планируем задачи публикации
            try:
                async with session_factory() as session:
                    await card.refresh()
                    await schedule_post_tasks(session, card)
                    print(f"Scheduled post tasks for card {card.card_id}")
            except Exception as e:
                print(f"Error scheduling post tasks: {e}")
        
        # Уведомляем об изменении статуса, чтобы обновить сцены
        try:
            update_data = {
                "scene_name": "task-detail", # Или view-tasks, или где отображается задача
                "data_key": "selected_task",
                "data_value": str(card.card_id)
            }
            # Также обновляем user-task сцены (для исполнителя)
            await executors_api.post(ApiEndpoints.UPDATE_SCENES, data=update_data)
            
            update_data_user = {
                "scene_name": "user-task",
                "data_key": "task_id",
                "data_value": str(card.card_id)
            }
            await executors_api.post(ApiEndpoints.UPDATE_SCENES, data=update_data_user)

        except Exception as e:
            print(f"Error updating scenes on status change: {e}")

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
                try:
                    await executors_api.delete(
                        ApiEndpoints.FORUM_DELETE_MESSAGE.value.format(card.card_id)
                    )
                    await card.update(forum_message_id=None)
                except Exception as e:
                    print(f"Error deleting forum message: {e}")

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
            
            # Закрываем все сцены, связанные с этой задачей
            try:
                # Закрываем сцены редактирования (user-task)
                update_data_user = {
                    "scene_name": "user-task",
                    "data_key": "task_id",
                    "data_value": str(card.card_id)
                }

                await executors_api.post(ApiEndpoints.UPDATE_SCENES, data=update_data_user)

                # Обновляем сцены просмотра (task-detail)
                update_data_view = {
                    "scene_name": "task-detail",
                    "data_key": "selected_task",
                    "data_value": str(card.card_id)
                }
                await executors_api.post(ApiEndpoints.UPDATE_SCENES, data=update_data_view)
                
            except Exception as e:
                print(f"Error closing scenes: {e}")

    if 'executor_id' in data and data['executor_id'] != card.executor_id:
        logger.info(f"Изменение исполнителя карточки {card.card_id}: {card.executor_id} -> {data['executor_id']}")

        user = await User.get_by_key(
            'user_id', data['executor_id']
        )
        if user and card.task_id != 0:
            tasker_id = user.tasker_id
            if tasker_id:

                async with kaiten as client:

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
    
    # Перепланируем задачи публикации при изменении send_time
    if send_time_changed:
        try:
            async with session_factory() as session:
                await card.refresh()
                await reschedule_post_tasks(session, card)
                print(f"Rescheduled post tasks for card {card.card_id}")
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
            try:
                # Определяем статус для отправки
                forum_status = card.status.value if hasattr(card.status, 'value') else str(card.status)
                
                # Вызываем обновление сообщения на форуме
                forum_result, forum_status_code = await executors_api.post(
                    ApiEndpoints.FORUM_UPDATE_MESSAGE,
                    data={
                        "card_id": str(card.card_id),
                        "status": forum_status
                    }
                )
                
                if forum_status_code != 200:
                    print(f"Failed to update forum message: {forum_result}")
            except Exception as e:
                print(f"Error updating forum message: {e}")
    
    # Отправляем уведомление исполнителю
    if card_data.notify_executor and card.executor_id:
        change_messages = {
            ChangeType.DEADLINE.value: '⏰ Изменен дедлайн',
            ChangeType.COMMENT.value: '💬 Добавлен комментарий',
            ChangeType.NAME.value: '✏️ Изменено название',
            ChangeType.DESCRIPTION.value: '📝 Изменено описание'
        }
        message_text = change_messages.get(card_data.change_type or '', Messages.CHANGE_NOTIFICATION.value)
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

    await card.update(executor_id=None)

    if card.task_id and card.task_id != 0:
        async with kaiten as client:
            await client.update_card(
                card.task_id,
                executor_id=None
            )

    return {"detail": "Executor removed successfully"}

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

    async with kaiten as client:
        try:
            await client.delete_card(card.task_id)
        except Exception as e:
            logger.error(f"Ошибка удаления карточки {card_id} из Kaiten: {e}")
            return {"detail": f"Card deleted from DB, but failed to delete from Kaiten: {e}"}

    try:
        if card.calendar_id:
            await delete_calendar_event(card.calendar_id)
    except Exception as e:
        logger.error(f"Ошибка удаления события календаря для карточки {card_id}: {e}")
        return {"detail": f"Card deleted from DB, but failed to delete from Calendar: {e}"}

    if card.forum_message_id:
        forum_res, status = await executors_api.delete(
                ApiEndpoints.FORUM_DELETE_MESSAGE.value.format(card.card_id)
            )

        if not forum_res.get('success', False):
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
    """Добавить комментарий к карточке (обычный комментарий)"""
    logger.info(f"Добавление комментария к карточке {note_data.card_id} от {note_data.author}")
    card = await Card.get_by_key('card_id', note_data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Добавляем комментарий в Kaiten
    if card.task_id and card.task_id != 0:
        try:
            # Получаем имя автора
            author = await User.get_by_key('user_id', note_data.author)
            author_name = "Unknown"
            if author:
                author_name = await get_kaiten_user_name(author)
            
            comment_text = f"💬 {author_name}: {note_data.content}"
            
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
    try:
        update_data = {
            "scene_name": SceneNames.USER_TASK,
            "data_key": "task_id",
            "data_value": str(note_data.card_id)
        }
        await executors_api.post(ApiEndpoints.UPDATE_SCENES, data=update_data)
    except Exception as e:
        logger.error(f"Ошибка обновления сцен: {e}")
    
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