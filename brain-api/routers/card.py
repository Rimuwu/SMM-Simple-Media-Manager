from datetime import datetime
from pprint import pprint
from typing import Optional
from uuid import UUID as _UUID
from os import getenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.connection import session_factory
from global_modules.classes.enums import CardType
from modules.kaiten import kaiten
from modules.properties import multi_properties
from modules.json_get import open_settings
from models.Card import Card, CardStatus
from modules.api_client import executors_api
from modules.calendar import create_calendar_event, delete_calendar_event, update_calendar_event
from models.User import User
from modules.scheduler import schedule_card_notifications, cancel_card_tasks, reschedule_card_notifications


# Создаём роутер
router = APIRouter(prefix='/card')
settings = open_settings() or {}

BOARD_ID = settings['space']['boards']['queue']['id']
COLUMN_ID = settings['space']['boards']['queue']['columns'][1]['id']

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

    # Преобразовываем текстомвые ключи в id свойств
    channels = []
    if card_data.channels:
        for channel in card_data.channels:
            if channel.isdigit():
                channels.append(int(channel))
            else:
                channels.append(
                    settings['properties']['channels']['values'][channel]['id']
            )

    tags = []
    if card_data.tags:
        for tag in card_data.tags:
            if tag.isdigit():
                tags.append(int(tag))
            else:
                tags.append(
                    settings['properties']['tags']['values'][tag]['id']
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
        print(f"Error in kaiten create card: {e}")
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

    if card_data.type_id == CardType.public:

        forum_res, status = await executors_api.post(
            "/forum/send-message-to-forum",
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
        try:
            executor = await User.get_by_key('user_id', card_data.executor_id)
            if executor:
                deadline_str = ""
                if card_data.deadline:
                    try:
                        deadline_dt = datetime.fromisoformat(card_data.deadline)
                        deadline_str = f"\n⏰ Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')}"
                    except:
                        pass
                
                message_text = f"🆕 Новая задача\n\n📝 {card_data.title}{deadline_str}\n\n{card_data.description}"
                await executors_api.post(
                    "/events/notify_user",
                    data={
                        "user_id": executor.telegram_id,
                        "message": message_text
                    }
                )
        except Exception as e:
            print(f"Error notifying executor about new task: {e}")

    # Планируем уведомления для карточки с дедлайном
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
            
            # Конвертируем бинарные данные
            if 'post_image' in card_dict and card_dict['post_image']:
                card_dict['post_image'] = card_dict['post_image'].hex() if isinstance(card_dict['post_image'], bytes) else None
            
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
    post_image: Optional[str] = None  # Hex-encoded binary data
    notify_executor: Optional[bool] = False  # Отправить уведомление исполнителю
    change_type: Optional[str] = None  # Тип изменения
    old_value: Optional[str] = None  # Старое значение
    new_value: Optional[str] = None  # Новое значение

@router.post("/update")
async def update_card(card_data: CardUpdate):
    print(card_data.__dict__)

    card = await Card.get_by_key('card_id', card_data.card_id)
    if not card:
        raise HTTPException(
            status_code=404, detail="Card not found")

    data = card_data.model_dump(exclude={'card_id'})
    data = {k: v for k, v in data.items() if v is not None}

    # Преобразуем hex-строку в bytes для post_image
    if 'post_image' in data and data['post_image']:
        try:
            data['post_image'] = bytes.fromhex(data['post_image'])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex format for post_image")

    # Преобразуем deadline в datetime
    if 'deadline' in data and isinstance(data['deadline'], str):
        try:
            data['deadline'] = datetime.fromisoformat(data['deadline'])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for deadline")

    # Преобразуем UUID поля
    for key in ['executor_id', 'customer_id']:
        if key in data and isinstance(data[key], str):
            try:
                data[key] = _UUID(data[key])
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid UUID format for {key}")

    if 'status' in data and data['status'] != card.status:

        if data['status'] == CardStatus.edited:
            board_id = settings['space'][
                'boards']['in_progress']['id']
            column_id = settings['space'][
                'boards']['in_progress']['columns'][0]['id']

            if card.task_id != 0:
                async with kaiten as client:
                    await client.update_card(
                        card.task_id,
                        board_id=board_id,
                        column_id=column_id
                    )

                    await client.add_comment(
                        card.task_id,
                        "Задание взято в работу"
                    )

    if 'executor_id' in data and data['executor_id'] != card.executor_id:

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

    # Обработка изменения deadline
    deadline_changed = False
    if 'deadline' in data and card.task_id and card.task_id != 0:
        deadline_changed = True
        try:
            async with kaiten as client:
                # Обновляем deadline в Kaiten
                await client.update_card(
                    card.task_id,
                    due_date=data['deadline'].strftime('%Y-%m-%d')
                )
                
                # Добавляем комментарий об изменении
                if card_data.old_value and card_data.new_value:
                    try:
                        old_dt = datetime.fromisoformat(card_data.old_value)
                        new_dt = datetime.fromisoformat(card_data.new_value)
                        comment = f"Дедлайн изменен: {old_dt.strftime('%d.%m.%Y %H:%M')} → {new_dt.strftime('%d.%m.%Y %H:%M')}"
                        await client.add_comment(card.task_id, comment)
                    except:
                        await client.add_comment(card.task_id, "Дедлайн изменен")
        except Exception as e:
            print(f"Error updating Kaiten card deadline: {e}")
        
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

    await card.update(**data)
    
    # Перепланируем задачи при изменении дедлайна
    if deadline_changed:
        try:
            async with session_factory() as session:
                await card.refresh()
                await reschedule_card_notifications(session, card)
        except Exception as e:
            print(f"Error rescheduling card notifications: {e}")
    
    # Обновляем сообщение на форуме если есть forum_message_id и изменились важные данные
    if card.forum_message_id:
        # Список полей, при изменении которых нужно обновить сообщение на форуме
        forum_update_fields = ['status', 'executor_id', 'deadline', 'name', 'description', 'content']
        should_update_forum = any(field in data for field in forum_update_fields)
        
        if should_update_forum:
            try:
                # Определяем статус для отправки
                forum_status = card.status.value if hasattr(card.status, 'value') else str(card.status)
                
                # Вызываем обновление сообщения на форуме
                forum_result, forum_status_code = await executors_api.post(
                    "/forum/update-forum-message",
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
        try:
            executor = await User.get_by_key('user_id', card.executor_id)
            if executor:
                change_messages = {
                    'deadline': '❓ Изменен дедлайн',
                    'comment': '💬 Добавлен комментарий'
                }
                message_text = change_messages.get(card_data.change_type, '🔔 Изменение в задаче')
                message_text += f"\n\n📝 Задача: {card.name}"
                
                if card_data.change_type == 'deadline' and card_data.new_value:
                    try:
                        new_dt = datetime.fromisoformat(card_data.new_value)
                        message_text += f"\n⏰ Новый дедлайн: {new_dt.strftime('%d.%m.%Y %H:%M')}"
                    except:
                        pass
                
                await executors_api.post(
                    "/events/notify_user",
                    data={
                        "user_id": executor.telegram_id,
                        "message": message_text
                    }
                )
        except Exception as e:
            print(f"Error notifying executor: {e}")
    
    # Возвращаем словарь без бинарных данных
    result = card.to_dict()
    if 'post_image' in result:
        # Удаляем бинарные данные из ответа или конвертируем в hex
        result['post_image'] = result['post_image'].hex() if result['post_image'] else None
    
    return result

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
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        raise HTTPException(
            status_code=404, detail="Card not found")

    # Удаляем все запланированные задачи для карточки
    try:
        async with session_factory() as session:
            await cancel_card_tasks(session, card_id)
    except Exception as e:
        print(f"Error canceling card tasks: {e}")

    await card.delete()

    async with kaiten as client:
        try:
            await client.delete_card(card.task_id)
        except Exception as e:
            return {"detail": f"Card deleted from DB, but failed to delete from Kaiten: {e}"}

    try:
        if card.calendar_id:
            await delete_calendar_event(card.calendar_id)
    except Exception as e:
        return {"detail": f"Card deleted from DB, but failed to delete from Calendar: {e}"}

    if card.forum_message_id:
        forum_res, status = await executors_api.post(
                f"/forum/delete-forum-message/{card_id}"
            )

        if not forum_res.get('success', False):
            return {"detail": "Card deleted from DB, but failed to delete forum message"}

    return {"detail": "Card deleted successfully"}

class CommentAdd(BaseModel):
    card_id: str
    content: str
    author: str  # user_id автора комментария

@router.post("/add-comment")
async def add_comment(note_data: CommentAdd):
    """Добавить комментарий к карточке (обычный комментарий)"""
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
                if author.tasker_id:
                    async with kaiten as client:
                        users = await client.get_users()
                        kaiten_user = next((u for u in users if u.id == author.tasker_id), None)
                        if kaiten_user:
                            author_name = kaiten_user.full_name
                if author_name == "Unknown":
                    # Используем telegram_id
                    author_name = f"@{author.telegram_id}"
            
            comment_text = f"💬 {author_name}: {note_data.content}"
            
            async with kaiten as client:
                await client.add_comment(card.task_id, comment_text)
        except Exception as e:
            print(f"Error adding comment to Kaiten: {e}")
    
    # Отправляем уведомление исполнителю
    if card.executor_id:
        try:
            executor = await User.get_by_key('user_id', card.executor_id)
            if executor:
                message_text = f"💬 Новый комментарий к задаче\n\n📝 {card.name}\n\n{note_data.content}"
                await executors_api.post(
                    "/events/notify_user",
                    data={
                        "user_id": executor.telegram_id,
                        "message": message_text
                    }
                )
        except Exception as e:
            print(f"Error notifying executor: {e}")
    
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
            async with kaiten as client:
                # Получаем информацию о пользователе
                user = await User.get_by_key('user_id', note_data.author)
                author_name = f"User {note_data.author}"
                if user and user.tasker_id:
                    # Получаем имя из Kaiten
                    users = await client.get_company_users(only_virtual=True)
                    kaiten_user = next((u for u in users if u['id'] == user.tasker_id), None)
                    if kaiten_user:
                        author_name = kaiten_user['full_name']
                
                comment_text = f"💬 Комментарий от {author_name}:\n{note_data.content}"
                await client.add_comment(card.task_id, comment_text)
        except Exception as e:
            print(f"Error adding comment to Kaiten: {e}")
    
    # Обновляем все открытые сцены с этой карточкой
    try:
        update_data = {
            "scene_name": "user-task",
            "data_key": "task_id",
            "data_value": str(note_data.card_id)
        }
        await executors_api.post("/events/update_scenes", data=update_data)
    except Exception as e:
        print(f"Error updating scenes: {e}")
    
    return {
        "detail": "Note added successfully",
        "note": new_note,
        "total_notes": len(editor_notes)
    }