from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from modules.constants import SETTINGS

group_forum = SETTINGS.get('group_forum', 0)

class InDMorWorkGroup(BaseFilter):

    async def __call__(self, 
                       var: Union[CallbackQuery, Message]
                       ) -> bool:

        if isinstance(var, CallbackQuery):
            message = var.message
        elif isinstance(var, Message):
            message = var

        if message.chat.type == 'private' or message.chat.id == int(group_forum):
            return True
        return False