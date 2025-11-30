from tg.oms import Page
from modules.api_client import get_users
from tg.oms.utils import callback_generator
from tg.oms.common_pages import UserSelectorPage
from modules.api_client import brain_api

class UsersListPage(Page):
    __page_name__ = 'users-list'


    async def buttons_worker(self) -> list[dict]:
        users = await get_users()
        buttons = []
        
        roles = {
            'admin': '👑',
            'customer': '🎩',
            'copywriter': '👤',
            'editor': '🖋️'
        }
        
        kaiten_users_list, kaiten_status = await brain_api.get(
                '/kaiten/get-users',
                params={'only_virtual': 1}
            )
        
        for user in users:
            role_icon = roles.get(user['role'], "👤")

            name = await UserSelectorPage.get_display_name(
                user, kaiten_users_list, self.scene.bot
            )
            buttons.append({
                "text": f"{role_icon} {name}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "user-detail",
                    str(user['telegram_id'])
                )
            })
            
        buttons.append({
            "text": "➕ Добавить пользователя",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "add-user"
            ),
            "ignore_row": True
        })

        return buttons

    @Page.on_callback('user-detail')
    async def on_user_detail(self, callback, args):
        telegram_id = int(args[1])

        await self.scene.update_key('scene', 
                                    'selected_user', telegram_id)
        await self.scene.update_page('user-detail')

    @Page.on_callback('add-user')
    async def on_add_user(self, callback, args):

        await self.scene.update_key('scene', 
                                    'selected_role', None)
        await self.scene.update_key('select-role', 
                                    'selected_role', None)

        await self.scene.update_key('scene', 
                                    'selected_kaiten_id', None)
        await self.scene.update_key('select-kaiten-user', 
                                    'selected_kaiten_id', None)
        await self.scene.update_page('add-user')
