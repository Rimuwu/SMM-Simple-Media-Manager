from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from modules.api_client import get_users

class Authorize(BaseFilter):

    async def __call__(self, 
                       var: Union[CallbackQuery, Message]
                       ) -> bool:
        telegram_id = None

        if type(var) == CallbackQuery:
            if var.message:
                telegram_id = var.from_user.id
            else: return False

        elif type(var) == Message:
            if var:
                telegram_id = var.from_user.id
            else: return False

        users = await get_users(telegram_id=telegram_id)
        return len(users) > 0
