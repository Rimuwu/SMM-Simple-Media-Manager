from datetime import datetime
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from modules.kaiten import kaiten
from modules.properties import multi_properties
from modules.json_get import open_settings
from models.Card import Card, CardStatus
from modules.api_client import executors_api

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

    executor_id: Optional[str]  # ID исполнителя в базе данных
    customer_id: Optional[str]  # ID заказчика в базе данных

    # properties
    channels: Optional[list[str]]  # Список каналов для публикации
    editor_check: bool  # Нужно ли проверять перед публикацией
    image_prompt: Optional[str]  # Промпт задачи для картинки
    tags: Optional[list[str]]  # Теги для карты
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

    forum_res, status = await executors_api.post(
        "/forum/send-message-to-forum",
            data={
                "title": card_data.title,
                "deadline": card_data.deadline or None,
                "description": card_data.description or ""
            }
    )
    if not status:
        return {"error": res.get("error", "Unknown error"), "success": False}

    message_id = forum_res.get("message_id", None)
    await card.update(forum_message_id=message_id)

    print(card.card_id, type(card.card_id))
    return {"card_id": card.card_id}