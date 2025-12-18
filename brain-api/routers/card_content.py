from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.Card import Card
from modules import card_events
from modules.kaiten import add_kaiten_comment
from modules.logs import brain_logger as logger

router = APIRouter()

class SetContentRequest(BaseModel):
    card_id: str
    content: str
    client_key: Optional[str] = None  # None означает установку общего контента ('all')

@router.post("/set-content")
async def set_content(request: SetContentRequest):
    """Установить контент для карточки.

    Если client_key не указан - устанавливает общий контент (ключ 'all').
    Если client_key указан - устанавливает контент для конкретного клиента.
    """
    logger.info(f"Установка контента для карточки {request.card_id}, клиент: {request.client_key or 'all'}")

    card = await Card.get_by_key('card_id', request.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Используем функцию on_content для установки контента
    await card_events.on_content(
        new_content=request.content,
        card=card,
        client_key=request.client_key
    )

    await card.refresh()
    return {"success": True, "card_id": str(card.card_id)}


class ClearContentRequest(BaseModel):
    card_id: str
    client_key: Optional[str] = None  # None означает очистку общего контента ('all')

@router.post("/clear-content")
async def clear_content(request: ClearContentRequest):
    """Очистить контент для карточки.

    Если client_key не указан - очищает общий контент (ключ 'all').
    Если client_key указан - очищает контент для конкретного клиента.
    """
    logger.info(f"Очистка контента для карточки {request.card_id}, клиент: {request.client_key or 'all'}")

    card = await Card.get_by_key('card_id', request.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Определяем ключ для очистки (None означает общий контент)
    key = request.client_key if request.client_key else None

    # Получаем все записи контента для карточки и очищаем нужные
    contents = await card.get_content(client_key=key)
    if contents:
        for c in contents:
            await c.delete()

        # Добавляем комментарий в Kaiten
        if card.task_id and card.task_id != 0:
            comment = f"🗑 Контент очищен для {'клиента: ' + request.client_key if request.client_key else 'общего контента'}"
            await add_kaiten_comment(card.task_id, comment)

    await card.refresh()
    return {"success": True, "card_id": str(card.card_id), "cleared_key": key}
