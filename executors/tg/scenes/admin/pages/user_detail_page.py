from tg.oms import Page
from modules.api_client import get_users, delete_user
from tg.oms.utils import callback_generator

class UserDetailPage(Page):
    __page_name__ = 'user-detail'

    async def data_preparate(self) -> None:
        user_id = self.scene.data['scene'].get('selected_user')
        if not user_id: return

        self.user = None
        users = await get_users(telegram_id=user_id)
        if not users: return

        self.user = users[0]
        role = self.user['role']
        kaiten_id = self.user['tasker_id']

        await self.scene.update_key('scene', 
                                    'selected_role', role)
        await self.scene.update_key('select-role', 
                                    'selected_role', role)

        await self.scene.update_key('scene', 
                                    'selected_kaiten_id', kaiten_id)
        await self.scene.update_key('select-kaiten-user', 
                                    'selected_kaiten_id', kaiten_id)

    async def content_worker(self) -> str:
        if not self.user:
            return "❌ Пользователь не найден."

        return self.content.format(
            telegram_id=self.user['telegram_id'],
            role=self.user['role'],
            tasker_id=self.user.get('tasker_id', 'Не привязан')
        )

    async def buttons_worker(self):
        user_id = self.scene.data['scene'].get('selected_user')
        return [
            {
                "text": "🎭 Изменить роль",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "select-role"
                )
            },
            {
                "text": "🆔 Изменить Kaiten ID",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "select-kaiten-user"
                )
            },
            {
                "text": "❌ Удалить пользователя",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "delete-user"
                ),
                "ignore_row": True
            },
            {
                "text": "🔙 Назад",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "users-list"
                ),
                "ignore_row": True
            }
        ]

    @Page.on_callback('delete-user')
    async def on_delete(self, callback, args):
        user_id = self.scene.data['scene'].get('selected_user')
        await delete_user(user_id)

        await callback.answer("✅ Пользователь удалён")
        await self.scene.update_page('users-list')

    @Page.on_callback('select-role')
    async def on_select_role(self, callback, args):
        await self.scene.update_key('scene', 'edit_mode', True)
        await self.scene.update_page('select-role')

    @Page.on_callback('select-kaiten-user')
    async def on_select_kaiten(self, callback, args):
        await self.scene.update_key('scene', 'edit_mode', True)
        await self.scene.update_page('select-kaiten-user')

    @Page.on_callback('users-list')
    async def on_back(self, callback, args):
        await self.scene.update_page('users-list')
