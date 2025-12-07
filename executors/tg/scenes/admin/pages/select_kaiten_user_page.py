from tg.oms.models.radio_page import RadioTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.brain_client import brain_client

class SelectKaitenUserPage(RadioTypeScene):
    __page_name__ = 'select-kaiten-user'
    __scene_key__ = 'selected_kaiten_id'
    
    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def data_preparate(self):
        # Загружаем виртуальных пользователей Kaiten
        kaiten_users_list = await brain_client.get_kaiten_users()
        
        if kaiten_users_list:
            self.options = {
                user['id']: f"{user['full_name']}"
                for user in kaiten_users_list
            }

        await super().data_preparate()

    async def buttons_worker(self):
        buttons = await super().buttons_worker()
        
        edit_mode = self.scene.data['scene'].get('edit_mode')
        back_page = 'user-detail' if edit_mode else 'select-role'

        buttons.append({
            "text": "❌ Не привязывать",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                'radio', '0'
            ),
            "ignore_row": True
        })

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

    @Page.on_callback('select-role')
    async def on_select_role_back(self, callback, args):
        await self.scene.update_page('select-role')

    async def on_selected(self, callback, selected_value):
        """Переопределяем метод из RadioTypeScene для кастомной логики"""
        tasker_id_str = selected_value
        tasker_id = int(tasker_id_str) if tasker_id_str != '0' else None
        
        edit_mode = self.scene.data['scene'].get('edit_mode')
        
        if edit_mode:
            user_id = self.scene.data['scene'].get('selected_user')
            await brain_client.update_user(user_id, tasker_id=tasker_id)
            await self.scene.update_key('scene', 'edit_mode', False)
            await self.scene.update_page('user-detail')

        else:
            await self.scene.update_key('scene',
                                        'new_user_tasker_id', tasker_id)
            await self.scene.update_page('select-department')

