from tg.oms.models.radio_page import RadioTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.classes.enums import Department
from modules.api_client import update_user

class SelectDepartmentPage(RadioTypeScene):
    __page_name__ = 'select-department'
    __scene_key__ = 'selected_department'
    
    def __after_init__(self):
        super().__after_init__()
        
        # Маппинг отделов на читаемые названия
        department_names = {
            "it": "IT",
            "design": "Дизайн",
            "cosplay": "Косплей",
            "craft": "Крафт",
            "media": "Медиа",
            "board_games": "Настольные игры",
            "smm": "SMM",
            "judging": "Судейство",
            "streaming": "Стриминг",
            "without_department": "Без отдела"
        }
        
        self.options = {
            dept.value: department_names.get(dept.value, dept.value)
            for dept in Department
        }
        self.next_page = ''

    async def buttons_worker(self):
        buttons = await super().buttons_worker()

        edit_mode = self.scene.data['scene'].get('edit_mode')
        back_page = 'user-detail' if edit_mode else 'select-kaiten-user'

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

    @Page.on_callback('select-kaiten-user')
    async def on_select_kaiten_back(self, callback, args):
        await self.scene.update_page('select-kaiten-user')

    async def on_selected(self, callback, selected_value):
        """Переопределяем метод из RadioTypeScene для кастомной логики"""
        department = selected_value

        edit_mode = self.scene.data['scene'].get('edit_mode')
        if edit_mode:
            user_id = self.scene.data['scene'].get('selected_user')
            await update_user(user_id, department=department)

            await self.scene.update_key('scene', 
                                        'edit_mode', False)
            await self.scene.update_page('user-detail')

        else:
            await self.scene.update_key('scene',
                                        'new_user_department', department)
            await self.scene.update_page('edit-about')
