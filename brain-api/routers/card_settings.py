from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.Card import Card
from global_modules.json_get import open_clients
from modules.settings import vk_executor, all_settings, tg_executor
from modules.logs import brain_logger as logger

router = APIRouter()

class CardSettings(BaseModel):
    card_id: str
    client_id: str
    setting_type: str
    data: dict

@router.post("/set-client_settings")
async def set_client_settings_endpoint(data: CardSettings):
    """ Установка настроек клиентов для карточки  """

    card = await Card.get_by_key('card_id', data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Убедимся, что клиент настроен для карточки
    if data.client_id not in (card.clients or []):
        raise HTTPException(status_code=400, detail="Client ID not found in card settings")

    clients = open_clients() or {}
    executor_type = clients.get(
        data.client_id, {}).get('executor_name') or clients.get(
        data.client_id, {}).get('executor')

    types = all_settings.avaibale_types.copy()
    if executor_type == 'vk_executor':
        types.update(vk_executor.avaibale_types)

    elif executor_type == 'telegram_executor':
        types.update(tg_executor.avaibale_types)

    if data.setting_type not in types:
        raise HTTPException(status_code=400, detail="Invalid setting type for client")

    if executor_type == 'vk_executor':
        res, error = await vk_executor.avaibale_types[
            data.setting_type](
            card, data.client_id, data.data
        )

    elif executor_type == 'telegram_executor':
        res, error = await tg_executor.avaibale_types[
            data.setting_type](
            card, data.client_id, data.data
        )

    return res, error
