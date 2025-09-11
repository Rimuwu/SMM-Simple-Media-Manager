from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from modules.apiclient import get_user_role

class RoleFilter(BaseFilter):
    def __init__(self, need_role: str) -> None:
        self.need_role = need_role

    async def __call__(self, var: Union[CallbackQuery, Message]) -> bool:
        telegram_id = None

        if type(var) == CallbackQuery:
            if var.message:
                telegram_id = var.from_user.id
            else: return False

        elif type(var) == Message:
            if var:
                telegram_id = var.from_user.id
            else: return False

        if telegram_id is None: return False
        user_role = await get_user_role(telegram_id)
        if user_role is None: return False
        return user_role == self.need_role or user_role == "admin"
