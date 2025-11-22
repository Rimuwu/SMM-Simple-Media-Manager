from datetime import datetime
from pprint import pprint
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.kaiten import kaiten
from modules.properties import multi_properties
from modules.json_get import open_settings
from models.Card import Card, CardStatus
from modules.api_client import executors_api
from modules.calendar import create_calendar_event, delete_calendar_event
from models.User import User


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

    executor_id: Optional[str] = None # ID исполнителя в базе данных
    customer_id: Optional[str] = None # ID заказчика в базе данных

    # properties
    channels: Optional[list[str]] = None  # Список каналов для публикации
    editor_check: bool = True # Нужно ли проверять перед публикацией
    image_prompt: Optional[str] = None  # Промпт задачи для картинки
    tags: Optional[list[str]] = None  # Теги для карты
    type_id: str  # Тип задания


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
        image_prompt=card_data.image_prompt,
        customer_id=card_data.customer_id,
        executor_id=card_data.executor_id,
    )

    if card_data.type_id == 'public':

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

        data = await create_calendar_event(
            card_data.title,
            card_data.description,
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
    query = {
        "task_id": task_id,
        "card_id": card_id,
        "status": status,
        "customer_id": customer_id,
        "executor_id": executor_id,
        "need_check": need_check,
        "forum_message_id": forum_message_id
    }
    # Убираем None значения из запроса
    query = {k: v for k, v in query.items() if v is not None}

    cards = await Card.filter_by(**query)
    if not cards:
        raise HTTPException(
            status_code=404, detail="Card not found")

    return [card.to_dict() for card in cards]

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
    image_prompt: Optional[str] = None
    prompt_sended: Optional[bool] = None
    calendar_id: Optional[str] = None

@router.post("/update")
async def update_card(card_data: CardUpdate):

    card = await Card.get_by_key('card_id', card_data.card_id)
    if not card:
        raise HTTPException(
            status_code=404, detail="Card not found")

    data = card_data.model_dump(exclude={'card_id'})
    data = {k: v for k, v in data.items() if v is not None}

    if card_data.status != card.status:

        if card_data.status == CardStatus.edited:
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

    if card_data.executor_id != card.executor_id:

        user = await User.get_by_key(
            'user_id', card_data.executor_id
        )
        if user and card.task_id != 0:
            tasker_id = user.tasker_id
            if tasker_id:

                async with kaiten as client:

                    await client.add_card_member(
                        card.task_id,
                        tasker_id
                    )
    
    print("Updating card:", data)

    await card.update(**data)
    return card.to_dict()

@router.delete("/delete/{card_id}")
async def delete_card(card_id: str):
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        raise HTTPException(
            status_code=404, detail="Card not found")

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