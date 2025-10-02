# Импортируем необходимые модули FastAPI
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.kaiten import kaiten
from modules.properties import multi_properties
from modules.json_get import open_settings

# Создаём роутер
router = APIRouter(prefix='/card')
settings = open_settings() or {}

BOARD_ID = settings.get('BOARD_ID', 0)
COLUMN_ID = settings.get('COLUMN_ID', 0)

# Модель данных для создания карты
class CardCreate(BaseModel):
    title: str
    description: str
    type_id: int
    # properties: dict[str, Any] #  'id_{custom_property_id}: value'
    deadline: str  # ISO 8601 format (due_date)

    # properties
    channels: list[str]  # Список каналов для публикации
    publish_date: str  # Дата и время публикации в формате ISO 8601
    editor_check: bool  # Нужно ли проверять перед публикацией
    image_prompt: str  # Промпт задачи для картинки
    tags: list[str]  # Теги для карты


@router.post("/create", response_model=CardCreate)
async def create_card(card_data: CardCreate):
    # Здесь будет логика создания карты

    properties = multi_properties(
        channels=card_data.channels,
        publish_date=card_data.publish_date,
        editor_check=card_data.editor_check,
        image_prompt=card_data.image_prompt,
        tags=card_data.tags
    )

    async with kaiten as client:

        res = await client.create_card(
            card_data.title,
            COLUMN_ID,
            card_data.description,
            BOARD_ID,
            due_date=card_data.deadline, properties=properties
        )

        print(res)

    return res

@router.get("/test-post")
async def test_post():
    
    properties = multi_properties(
        channels=[1], #['Киберкужок', 'ТГ Настолки'],
        # publish_date={
        #     "value": "2025-12-31T10:00:00Z"
        #     },
        editor_check=True,
        image_prompt='Создать изображение для карты',
        tags= [1]#['Content']
    )

    async with kaiten as client:

        res = await client.create_card(
            'Test Card from API',
            COLUMN_ID,
            'This is a test card created from the API',
            BOARD_ID,
            due_date='2025-12-25', 
            properties=properties
        )

    return res
