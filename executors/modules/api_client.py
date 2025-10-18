from typing import Optional
from global_modules.api_client import APIClient
from global_modules.classes.enums import CardStatus

brain_api = APIClient('http://brain:8000')

async def get_user_role(telegram_id: int) -> str | None:
    """Получить роль пользователя по telegram_id"""
    user, status_code = await brain_api.get(f"/user/get",
                        params={"telegram_id": telegram_id})
    if status_code == 200 and user:
        return user[0]['role']
    return None

async def get_cards(task_id: Optional[str] = None, 
              card_id: Optional[str] = None, 
              status: Optional[CardStatus] = None,
              customer_id: Optional[str] = None,
              executor_id: Optional[str] = None,
              need_check: Optional[bool] = None,
              forum_message_id: Optional[int] = None
              ):

    """Получить карточки по различным параметрам"""
    params = {
        "task_id": task_id,
        "card_id": card_id,
        "status": status,
        "customer_id": customer_id,
        "executor_id": executor_id,
        "need_check": need_check,
        "forum_message_id": forum_message_id
    }
    cards, res_status = await brain_api.get(
        "/card/get",
        params=params
    )

    if res_status != 200:
        return []

    return cards

async def update_card(card_id: str,
    status: Optional[CardStatus] = None,
    executor_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    need_check: Optional[bool] = None,
    forum_message_id: Optional[int] = None
    ):
    """Обновить карточку"""
    data = {
        "card_id": card_id,
        "status": status,
        "executor_id": executor_id,
        "customer_id": customer_id,
        "need_check": need_check,
        "forum_message_id": forum_message_id
    }
    card, res_status = await brain_api.post(
        f"/card/update",
        data=data
    )

    if res_status != 200:
        return None

    return card