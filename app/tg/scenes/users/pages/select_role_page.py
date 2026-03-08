from tg.oms.models.radio_page import RadioTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.enums import UserRole
from modules.exec.brain_client import brain_client
from tg.scenes.constants import ROLE_NAMES, ROLE_ICONS

class SelectRolePage(RadioTypeScene):
    __page_name__ = 'select-role'
    __scene_key__ = 'selected_role'

    def __after_init__(self):
        super().__after_init__()
        self.options = {
            role.value: f'{ROLE_ICONS[role.value]} {ROLE_NAMES[role.value]}' for role in UserRole
            }
        self.next_page = ''

    async def buttons_worker(self):
        buttons = await super().buttons_worker()

        edit_mode = self.scene.data['scene'].get('edit_mode')
        back_page = 'user-detail' if edit_mode else 'add-user'

        buttons.append({
            "text": "🔙 Назад",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                back_page
            ),
            "ignore_row": True
        })
        return buttons

    @Page.on_callback('user-detail')
    async def on_user_detail_back(self, callback, args):
        await self.scene.update_page('user-detail')

    @Page.on_callback('add-user')
    async def on_add_user_back(self, callback, args):
        await self.scene.update_page('add-user')

    async def on_selected(self, callback, selected_value):
        """Переопределяем метод из RadioTypeScene для кастомной логики"""
        role = selected_value

        edit_mode = self.scene.data['scene'].get('edit_mode')
        if edit_mode:
            user_id = self.scene.data['scene'].get('selected_user')
            await brain_client.update_user(user_id, role=role)

            await self.scene.update_key('scene', 
                                        'edit_mode', False)
            await self.scene.update_page('user-detail')

        else:
            await self.scene.update_key('scene',
                                        'new_user_role', role)
            await self.scene.update_page('select-department')

