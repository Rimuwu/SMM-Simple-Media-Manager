# Импортируем необходимые модули FastAPI
from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from modules.kaiten import kaiten
from modules.properties import multi_properties
from modules.json_get import open_settings

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

    # properties
    channels: Optional[list[str]]  # Список каналов для публикации
    editor_check: bool  # Нужно ли проверять перед публикацией
    image_prompt: Optional[str]  # Промпт задачи для картинки
    tags: Optional[list[str]]  # Теги для карты
    type_id: str  # Тип задания


@router.post("/create", response_model=CardCreate)
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
            position=1
        )

    return res