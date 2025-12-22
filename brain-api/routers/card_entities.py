from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.Card import Card
from global_modules.json_get import open_clients
from modules.kaiten import add_kaiten_comment
from modules.entities import avaibale_entities
from modules.logs import brain_logger as logger
from models.Entity import Entity
from modules.card_events import on_entities

router = APIRouter()

class AddEntityRequest(BaseModel):
    card_id: str
    client_id: str
    entity_type: str
    data: dict
    name: Optional[str] = None


@router.post("/add-entity")
async def add_entity_endpoint(req: AddEntityRequest):
    """Добавляет entity (например опрос) для конкретного клиента внутри карточки"""
    card = await Card.get_by_key('card_id', req.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if req.client_id not in (card.clients or []):
        raise HTTPException(status_code=400, detail="Client ID not found in card clients")

    clients = open_clients() or {}
    executor_type = clients.get(req.client_id, {}).get('executor_name')

    handlers = avaibale_entities.get(executor_type, {})
    handler = handlers.get(req.entity_type)
    if not handler:
        raise HTTPException(status_code=400, detail="Invalid entity type for client")

    normalized = handler(req.data)
    data = normalized if isinstance(normalized, dict) else {'value': normalized}
    if req.name:
        data['name'] = req.name

    ent = await Entity.create(card_id=card.card_id, 
                              client_key=req.client_id, 
                              data=data, type=req.entity_type)

    await on_entities(req.client_id, card=card)

    if card.task_id and card.task_id != 0:
        comment = f"🧩 Добавлен entity: {req.entity_type} для клиента {req.client_id}"
        await add_kaiten_comment(card.task_id, comment)

    return {"entity": ent.to_dict()} 


@router.get('/entities')
async def list_entities(card_id: str, 
                        client_id: str):
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    rows = await Entity.filter_by(card_id=card.card_id, client_key=client_id)
    return {"entities": [r.to_dict() for r in rows]} 


@router.get('/entity')
async def get_entity(card_id: str, client_id: str, entity_id: str):
    card = await Card.get_by_key('card_id', card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    ent = await Entity.get_by_key('id', entity_id)
    if not ent or str(ent.card_id) != str(card.card_id) or ent.client_key != client_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    return ent.to_dict()


class DeleteEntityRequest(BaseModel):
    card_id: str
    client_id: str
    entity_id: str

@router.post('/delete-entity')
async def delete_entity(req: DeleteEntityRequest):
    card = await Card.get_by_key('card_id', req.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    ent = await Entity.get_by_key('id', req.entity_id)
    if not ent or str(ent.card_id) != str(card.card_id) or ent.client_key != req.client_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    await ent.delete()
    await on_entities(req.client_id, card=card)

    # Kaiten comment
    if card.task_id and card.task_id != 0:
        comment = f"🗑 Удалён entity {req.entity_id} ({req.client_id})"
        await add_kaiten_comment(card.task_id, comment)

    return {"detail": "Entity deleted"}


class UpdateEntityRequest(BaseModel):
    card_id: str
    client_id: str
    entity_id: str
    data: dict
    name: Optional[str] = None

@router.post('/update-entity')
async def update_entity(req: UpdateEntityRequest):
    """Обновляет существующий entity для клиента внутри карточки"""
    card = await Card.get_by_key('card_id', req.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    ent = await Entity.get_by_key('id', req.entity_id)
    if not ent or str(ent.card_id) != str(card.card_id) or ent.client_key != req.client_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    clients = open_clients() or {}
    executor_type = clients.get(req.client_id, {}).get('executor_name')
    handlers = avaibale_entities.get(executor_type, {})
    handler = handlers.get(ent.type) if handlers else None

    normalized = req.data
    try:
        if handler:
            normalized = handler(req.data)
    except HTTPException:
        raise
    except Exception:
        pass

    data = normalized if isinstance(normalized, dict) else {'value': normalized}
    if req.name is not None:
        data['name'] = req.name
    data['updated_at'] = datetime.now().isoformat()

    await ent.update(data=data)
    await on_entities(req.client_id, card=card)

    if card.task_id and card.task_id != 0:
        comment = f"✏️ Обновлён entity {req.entity_id} ({req.client_id})"
        await add_kaiten_comment(card.task_id, comment)

    ent = await Entity.get_by_key('id', req.entity_id)
    return {"entity": ent.to_dict() if ent else None}
