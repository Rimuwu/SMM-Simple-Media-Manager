from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import update_user

class EditAboutPage(TextTypeScene):
    __page_name__ = 'edit-about'
    __scene_key__ = 'about_text'
    
    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def data_preparate(self):
        # Данные уже установлены в user_detail_page, не нужно дублировать загрузку
        await super().data_preparate()

    async def buttons_worker(self):
        buttons = []

        edit_mode = self.scene.data['scene'].get('edit_mode')
        back_page = 'user-detail' if edit_mode else 'select-department'

        buttons.append({
            "text": "💾 Сохранить",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                'save-about'
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

    @Page.on_callback('save-about')
    async def on_save(self, callback, args):
        about_text = self.scene.data['scene'].get('about_text', '')

        edit_mode = self.scene.data['scene'].get('edit_mode')
        if edit_mode:
            user_id = self.scene.data['scene'].get('selected_user')
            await update_user(user_id, about=about_text)

            await self.scene.update_key('scene', 
                                        'edit_mode', False)
            await self.scene.update_page('user-detail')
            await callback.answer("✅ Описание обновлено")

        else:
            # Создаем пользователя со всеми данными
            from modules.api_client import create_user
            telegram_id = self.scene.data['scene'].get('new_user_id')
            role = self.scene.data['scene'].get('new_user_role')
            tasker_id = self.scene.data['scene'].get('new_user_tasker_id')
            department = self.scene.data['scene'].get('new_user_department')
            
            result = await create_user(
                telegram_id=telegram_id,
                role=role,
                tasker_id=tasker_id,
                department=department,
                about=about_text
            )
            
            if result:
                await callback.answer("✅ Пользователь создан")
                await self.scene.update_page('users-list')
            else:
                await callback.answer("❌ Ошибка создания")

    @Page.on_callback('user-detail')
    async def on_user_detail_back(self, callback, args):
        await self.scene.update_page('user-detail')

    @Page.on_callback('select-department')
    async def on_select_department_back(self, callback, args):
        await self.scene.update_page('select-department')

    async def on_text_input(self, message, text):
        """Переопределяем метод из TextTypeScene"""
        await self.scene.update_key('scene', 'about_text', text)
        await self.scene.update_message()
