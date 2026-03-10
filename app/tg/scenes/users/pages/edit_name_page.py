from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from models.User import User


class EditNamePage(TextTypeScene):
    __page_name__ = 'edit-name'
    __scene_key__ = 'user_name'

    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def data_preparate(self):
        self.clear_content()
        user_id = self.scene.data['scene'].get('selected_user')

        if not user_id: return

        self.user = None
        users = [u.to_dict() for u in await User.find(telegram_id=user_id)]
        if not users: return

        self.user = users[0]
        self.user_name = self.user.get('name', 'Без имени')

        await super().data_preparate()

    async def buttons_worker(self):
        buttons = []

        edit_mode = self.scene.data['scene'].get('edit_mode')
        back_page = 'user-detail' if edit_mode else 'select-department'

        buttons.append({
            "text": "💾 Сохранить",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                'save-name'
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

    @Page.on_callback('save-name')
    async def on_save(self, callback, args):
        name_text = self.scene.data['scene'].get('user_name', '').strip()

        if not name_text:
            await callback.answer("⚠️ Введите имя", show_alert=True)
            return

        edit_mode = self.scene.data['scene'].get('edit_mode')
        if edit_mode:
            user_id = self.scene.data['scene'].get('selected_user')
            u = await User.get_by_key("telegram_id", user_id)
            if u:
                await u.update(name=name_text)
            await self.scene.update_key('scene', 'edit_mode', False)
            await self.scene.update_page('user-detail')
            await callback.answer("✅ Имя обновлено")
        else:
            await self.scene.update_page('edit-about')

    @Page.on_callback('skip-name')
    async def on_skip(self, callback, args):
        edit_mode = self.scene.data['scene'].get('edit_mode')
        if edit_mode:
            await self.scene.update_key('scene', 'edit_mode', False)
            await self.scene.update_page('user-detail')
        else:
            await self.scene.update_page('edit-about')

    @Page.on_callback('user-detail')
    async def on_user_detail_back(self, callback, args):
        await self.scene.update_page('user-detail')

    @Page.on_callback('select-department')
    async def on_select_department_back(self, callback, args):
        await self.scene.update_page('select-department')

    async def on_text_input(self, message, text):
        await self.scene.update_key('scene', 'user_name', text)
        await self.scene.update_message()

    async def page_leave(self):
        self.scene.data['scene']['user_name'] = None
        self.user_name = None

        return await super().page_leave()