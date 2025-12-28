from datetime import datetime, timedelta
import enum
from typing import Literal, Optional
from uuid import UUID as _UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.connection import session_factory
from global_modules.classes.enums import CardType
from global_modules.timezone import now_naive as moscow_now
from modules.kaiten import add_kaiten_comment, kaiten
from modules.properties import multi_properties
from global_modules.json_get import open_settings, open_properties
from models.Card import Card, CardStatus
from models.User import User
from modules.calendar import create_calendar_event, delete_calendar_event
from modules.scheduler import schedule_card_notifications, cancel_card_tasks,  schedule_post_tasks, update_post_tasks_time
from modules.constants import (
    KaitenBoardNames, PropertyNames, 
    SceneNames, Messages
)
from modules.card_service import (
    notify_executor, increment_customer_tasks
)
from modules.executors_client import (
    send_forum_message, delete_forum_message_by_id,
    delete_all_complete_previews, close_card_related_scenes,
)
from modules.logs import brain_logger as logger
from modules import status_changers
from modules import card_events
from models.CardMessage import CardMessage

router = APIRouter(prefix='/card')

try:
    from .card_settings import router as settings_router
    from .card_entities import router as entities_router
    from .card_content import router as content_router
    router.include_router(settings_router)
    router.include_router(entities_router)
    router.include_router(content_router)

except Exception:
    pass

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
    editor_id: Optional[str] = None  # ID редактора в базе данных

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
    properties_data = open_properties() or {}
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

            executor_ = await User.get_by_key(
                            'user_id', 
                            card_data.executor_id)
            customer_ = await User.get_by_key(
                            'user_id', 
                            card_data.customer_id)

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
                    kaiten_card = None

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

    # clients_settings = {
    #     key: {} for key in card_data.channels or []
    # }

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
        need_check=card_data.need_check,
        editor_id=card_data.editor_id,
    )

    # Создаём пустые настройки клиентов в отдельной таблице
    from models.ClientSetting import ClientSetting
    for key in card_data.channels or []:
        try:
            await ClientSetting.create(card_id=card.card_id, client_key=str(key), data={})
        except Exception:
            pass

    logger.info(f"Карточка создана в БД: {card.card_id} (Kaiten ID: {card_id})")

    # Увеличиваем счётчик созданных задач у заказчика
    if card_data.customer_id:
        await increment_customer_tasks(card_data.customer_id)

    if card_data.type_id == CardType.public:
        message_id, error = await send_forum_message(str(card.card_id))
        if error:
            print(f"Error in forum send: {error}")
        if message_id:
            await card.add_message('forum', message_id)

    try:
        if card_data.send_time is None:
            cal_date = datetime.fromisoformat(card_data.deadline) if card_data.deadline else None
        else:
            cal_date = datetime.fromisoformat(card_data.send_time)

        # Добавляем ссылку в описание
        calendar_description = f"{card_data.description}"

        data = await create_calendar_event(
            card_data.title,
            calendar_description,
            cal_date,
            cal_date + timedelta(minutes=60) if cal_date else None,
            all_day=False,
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
              editor_id: Optional[str] = None
              ):
    # Используем явный запрос с eager loading для связанных объектов
    async with session_factory() as session:
        stmt = select(Card).options(selectinload(Card.executor),
                                    selectinload(Card.customer),
                                    selectinload(Card.editor),
                                    selectinload(Card.editor_notes_entries),
                                    selectinload(Card.clients_settings_entries),
                                    selectinload(Card.entities_entries)
                                    )
    
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
        if editor_id:
            stmt = stmt.where(Card.editor_id == editor_id)
        if need_check:
            stmt = stmt.where(Card.need_check == need_check)

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
            executor = await User.get_by_key('user_id', card.executor_id)
            if executor:
                kaiten_name = kaiten_users.get(executor.tasker_id) if executor.tasker_id else None

                card_dict['executor'] = {
                    'user_id': str(executor.user_id),
                    'telegram_id': executor.telegram_id,
                    'tasker_id': executor.tasker_id,
                    'full_name': kaiten_name or f"@{executor.telegram_id}"
                }
            else:
                card_dict['executor'] = None

            # Backwards-compatible normalized fields: content, editor_notes, clients_settings, entities
            contents = await card.get_content(session=session)
            card_dict['content'] = {c.client_key or 'all': c.text for c in contents}

            notes = await card.get_editor_notes(session=session)
            card_dict['editor_notes'] = [n.to_dict() for n in notes]

            settings = await card.get_clients_settings(session=session)
            clients_settings = {}
            for s in settings:
                key = s.client_key or 'all'
                clients_settings.setdefault(key, {}).update(s.data or {})
            card_dict['clients_settings'] = clients_settings

            entities = await card.get_entities(session=session)
            entities_map = {}
            for e in entities:
                key = e.client_key or 'all'
                entities_map.setdefault(key, []).append(e.to_dict())
            card_dict['entities'] = entities_map

            result.append(card_dict)

        return result

class S(enum.Enum):
    Nothing = '__nothing__'

class CardUpdate(BaseModel):
    card_id: str

    name: Optional[str] | S = S.Nothing  # Название карточки
    description: Optional[str] | S = S.Nothing  # Описание карточки

    executor_id: Optional[str] | S = S.Nothing
    customer_id: Optional[str] | S = S.Nothing
    editor_id: Optional[str] | S = S.Nothing

    need_check: Optional[bool] | S = S.Nothing
    need_send: Optional[bool] | S = S.Nothing  # Нужно ли отправлять в каналы

    clients: Optional[list[str]] | S = S.Nothing
    tags: Optional[list[str]] | S = S.Nothing

    deadline: Optional[str] | S = S.Nothing  # ISO 8601 format
    send_time: Optional[str] | S = S.Nothing  # ISO 8601 format

    image_prompt: Optional[str] | S = S.Nothing
    prompt_message: Optional[int] | S = S.Nothing  # ID сообщения дизайнерам

    calendar_id: Optional[str] | S = S.Nothing
    post_images: Optional[list[str]] | S = S.Nothing  # Список имён файлов из Kaiten для публикации

    author_id: Optional[str] | S = S.Nothing  # ID пользователя, вносящего изменения

@router.post("/update")
async def update_card(card_data: CardUpdate):
    """
    Обновляет карточку через функции из card_events.
    НЕ меняет статус - для этого используйте /change-status
    """

    card = await Card.get_by_key('card_id', card_data.card_id)
    if not card:
        logger.warning(f"Попытка обновления несуществующей карточки: {card_data.card_id}")
        raise HTTPException(status_code=404, detail="Card not found")

    data = card_data.model_dump()
    data = {k: v for k, v in data.items() if v != S.Nothing}

    # Логируем ключи, которые меняются
    logger.info(f"Обновление карточки {card.card_id}: {list(data.keys())}")

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
    for key in ['executor_id', 'customer_id', 'editor_id']:
        if key in data and isinstance(data[key], str):
            try:
                data[key] = _UUID(data[key])
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid UUID format for {key}")

    # Изменение названия через card_events.on_name
    if 'name' in data:
        await card_events.on_name(data['name'], card=card)
        del data['name']

    # Изменение описания через card_events.on_description
    if 'description' in data:
        await card_events.on_description(data['description'], card=card)
        del data['description']

    # Изменение дедлайна через card_events.on_deadline
    if 'deadline' in data:
        old_deadline = card.deadline
        await card_events.on_deadline(data['deadline'], old_deadline, card=card)
        del data['deadline']

    # Изменение времени отправки через card_events.on_send_time
    if 'send_time' in data:
        await card_events.on_send_time(data['send_time'], card=card)
        del data['send_time']

    # Изменение исполнителя через card_events.on_executor
    if 'executor_id' in data:
        await card_events.on_executor(data['executor_id'], card=card)
        del data['executor_id']

    # Изменение редактора через card_events.on_editor
    if 'editor_id' in data:
        await card_events.on_editor(data['editor_id'], card=card)
        del data['editor_id']

    # Изменение каналов через card_events.on_clients
    if 'clients' in data:
        await card_events.on_clients(data['clients'], card=card)
        del data['clients']

    # Изменение need_check через card_events.on_need_check
    if 'need_check' in data:
        await card_events.on_need_check(data['need_check'], card=card)
        del data['need_check']

    # Изменение тегов через card_events.on_tags
    if 'tags' in data:
        await card_events.on_tags(data['tags'], card=card)
        del data['tags']

    # Изменение image_prompt через card_events.on_image_prompt
    if 'image_prompt' in data:
        await card_events.on_image_prompt(data['image_prompt'], card=card)
        del data['image_prompt']

    # Изменение prompt_message через card_events.on_prompt_message
    if 'prompt_message' in data:
        await card_events.on_prompt_message(data['prompt_message'], card=card)
        del data['prompt_message']

    # Изменение editor_notes через card_events.on_editor_notes
    if 'editor_notes' in data:
        await card_events.on_editor_notes(data['editor_notes'], card=card)
        del data['editor_notes']

    # Изменение clients_settings через card_events.on_clients_settings
    if 'clients_settings' in data:
        await card_events.on_clients_settings(data['clients_settings'], card=card)
        del data['clients_settings']

    # Изменение entities через card_events.on_entities
    if 'entities' in data:
        await card_events.on_entities(data['entities'], card=card)
        del data['entities']

    # Остальные поля обновляем напрямую (те что не требуют сложной логики)
    if data:
        await card.update(**data)

    await card.refresh()
    return card.to_dict()

class ChangeStatusRequest(BaseModel):
    card_id: str
    new_status: CardStatus
    who_changed: Optional[Literal['executor', 'admin']] = 'admin'  # 'executor' или 'admin'
    comment: Optional[str] = None  # Опциональный комментарий при смене статуса

@router.post("/change-status")
async def change_status(request: ChangeStatusRequest):
    """Изменить статус карточки через функции status_changers"""
    logger.info(f"Запрос на изменение статуса карточки {request.card_id} на {request.new_status}")

    # Загружаем карточку с eager loading для editor_notes_entries
    async with session_factory() as session:
        stmt = select(Card).options(
            selectinload(Card.editor_notes_entries)
            ).where(Card.card_id == request.card_id)
        result = await session.execute(stmt)
        card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Добавляем комментарий если он указан
    if request.comment:
        try:
            editor_notes = card.editor_notes or []
            new_note = {
                "content": request.comment,
                "author": "system",
                "created_at": datetime.now().isoformat(),
                "is_status_change": True
            }
            editor_notes.append(new_note)
            await card.update(editor_notes=editor_notes)
            
            # Добавляем в Kaiten
            if card.task_id and card.task_id != 0:
                await add_kaiten_comment(card.task_id, f"💬 Комментарий: {request.comment}")
        except Exception as e:
            logger.error(f"Ошибка добавления комментария при смене статуса: {e}")
    
    # Маппинг статусов на функции
    status_handlers = {
        CardStatus.pass_: status_changers.to_pass,
        CardStatus.edited: status_changers.to_edited,
        CardStatus.review: status_changers.to_review,
        CardStatus.ready: status_changers.to_ready,
        CardStatus.sent: status_changers.to_sent,
    }
    
    handler = status_handlers.get(request.new_status)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.new_status}")
    
    try:
        # Для to_pass передаём who_changed
        if request.new_status == CardStatus.pass_:
            await handler(card=card, who_changed=request.who_changed)
        else:
            await handler(card=card)

        logger.info(f"Статус карточки {request.card_id} успешно изменен на {request.new_status}")
        return {"detail": "Status changed successfully", "new_status": request.new_status.value}
    except Exception as e:
        logger.error(f"Ошибка изменения статуса карточки {request.card_id}: {e}")
        raise HTTPException(status_code=500, 
                            detail=f"Error changing status: {e}")


@router.delete("/delete/{card_id}")
async def delete_card(card_id: str):
    logger.info(f"Запрос на удаление карточки {card_id}")
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        logger.warning(f"Попытка удаления несуществующей карточки: {card_id}")
        raise HTTPException(
            status_code=404, detail="Card not found")

    # Удаляем все файлы карточки из storage_api
    try:
        from models.CardFile import CardFile
        files = await CardFile.filter_by(card_id=card_id)
        for card_file in files:
           await card_file.delete()
    except Exception as e:
        logger.error(f"Error deleting files for card {card_id}: {e}")

    # Удаляем сообщения форума и превью
    try:
        forum_msg = await card.get_forum_message()
        if forum_msg:
            if not await delete_forum_message_by_id(forum_msg.message_id):
                logger.warning(f"Ошибка удаления сообщения форума для карточки {card_id}")

        complete_msgs = await card.get_messages(message_type='complete_preview')
        if complete_msgs:
            await delete_all_complete_previews(complete_msgs)

        # Явно удаляем все CardMessage записи перед удалением карточки
        from models.CardMessage import CardMessage
        all_messages = await CardMessage.filter_by(card_id=card.card_id)
        for msg in all_messages:
            await msg.delete()
    except Exception as e:
        logger.warning(f"Error deleting messages for card {card_id}: {e}")
    
    await close_card_related_scenes(
        str(card.card_id))

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

    logger.info(f"Карточка {card_id} успешно удалена")
    return {"detail": "Card deleted successfully"}

class CommentAdd(BaseModel):
    card_id: str
    content: str
    author: str  # user_id автора комментария
    is_editor_note: bool = False  # True для комментария редактора, False для обычного комментария

@router.post("/add-comment")
async def add_comment(note_data: CommentAdd):
    """Добавить комментарий к карточке"""
    logger.info(
        f"Добавление комментария к карточке {note_data.card_id} от {note_data.author} (редактор: {note_data.is_editor_note})")

    card = await Card.get_by_key('card_id', note_data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Создаём новый комментарий
    new_note = {
        "content": note_data.content,
        "author": note_data.author,
    }

    await card_events.on_editor_notes(
        note_data.content, note_data.author,
        card=card
    )

    return {
        "note": new_note
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

@router.get("/get-messages")
async def get_messages(card_id: Optional[str] = None,
              message_type: Optional[str] = None):

    async with session_factory() as session:
        stmt = select(CardMessage).options()

        # Применяем фильтры
        if message_type:
            stmt = stmt.where(CardMessage.message_type == message_type)
        if card_id:
            stmt = stmt.where(CardMessage.card_id == _UUID(card_id))

        result_db = await session.execute(stmt)
        messages = result_db.scalars().all()

        if not messages:
            raise HTTPException(status_code=404, detail="Messages not found")

        return [msg.to_dict() for msg in messages]

@router.get("/get-card-by-message_id/{message_id}")
async def get_card_by_message_id(message_id: int):
    """Получить карточку по ID сообщения"""
    async with session_factory() as session:
        
        message = await CardMessage.filter_by(message_id=message_id)
        message = message[0] if message else None

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        card = await Card.get_by_key('card_id', message.card_id)
        if not card:
            raise HTTPException(status_code=414, detail="Card not found")

        return card.to_dict()