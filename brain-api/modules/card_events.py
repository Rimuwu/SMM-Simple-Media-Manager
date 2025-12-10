import asyncio
from typing import Literal, Optional
from uuid import UUID as _UUID
from models.Card import Card
from kaiten import update_kaiten_card_field
from executors_client import notify_users
from executors_client import update_scenes
from constants import SceneNames

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
    comment = f"✏️ Название изменено:\n{
        card.name} → {new_name}"

    await update_kaiten_card_field(
        card.task_id, 'title', 
        new_name, comment
    )
    await card.update(name=new_name)

    listeners = [
        card.executor.user_id if card.executor else None,
        card.editor.user_id if card.editor else None
    ]

    await notify_users(listeners, comment, 'change-name')

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


async def on_description(card: Optional[Card] = None, 
                         card_id: Optional[_UUID] = None):
    pass

async def on_deadline(card: Optional[Card] = None, 
                      card_id: Optional[_UUID] = None):
    pass

async def on_send_time(card: Optional[Card] = None, 
                       card_id: Optional[_UUID] = None):
    pass

async def on_executor(card: Optional[Card] = None, 
                      card_id: Optional[_UUID] = None):
    pass

async def on_editor(card: Optional[Card] = None, 
                    card_id: Optional[_UUID] = None):
    pass

async def on_content(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_clients(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_need_check(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_tags(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_image_prompt(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_prompt_message(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_forum_message_id(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_complete_message_id(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_editor_notes(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_clients_settings(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass

async def on_entities(card: Optional[Card] = None, card_id: Optional[_UUID] = None):
    pass