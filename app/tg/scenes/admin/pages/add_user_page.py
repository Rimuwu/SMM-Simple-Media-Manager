from tg.oms import Page
from tg.oms.utils import callback_generator

class AddUserPage(Page):
    __page_name__ = 'add-user'

    async def content_worker(self) -> str:
        return self.content

    @Page.on_text('int')
    async def text_worker(self, message, value: int):
        telegram_id = value
        await self.scene.update_key('scene', 'new_user_id', telegram_id)
        await self.scene.update_page('select-role')

    async def buttons_worker(self):
        return [{
            "text": "🔙 Назад",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "users-list"
            )
        }]

    @Page.on_callback('users-list')
    async def on_back(self, callback, args):
        await self.scene.update_page('users-list')
