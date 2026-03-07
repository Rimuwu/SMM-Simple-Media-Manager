from modules.utils import get_display_name
from tg.oms import Page
from global_modules.brain_client import brain_client
from tg.oms.utils import callback_generator
from global_modules.vault.vault_client import vault_getenv as getenv
from tg.scenes.constants import ROLE_NAMES, DEPARTMENT_NAMES as department_names

superuser_id = int(getenv("ADMIN_ID", 0))

class UserDetailPage(Page):
    __page_name__ = 'user-detail'

    async def data_preparate(self) -> None:
        user_id = self.scene.data['scene'].get('selected_user')
        if not user_id: return

        self.user = None
        users = await brain_client.get_users(telegram_id=user_id)
        if not users: return

        self.user = users[0]

        self.selected_role = ROLE_NAMES.get(self.user['role'])
        self.selected_department = self.user.get('department')
        self.about_text = self.user.get('about', '')

    async def content_worker(self) -> str:
        if not self.user:
            return "❌ Пользователь не найден."

        department_value = self.user.get('department', 'Не указан')
        department_display = department_names.get(department_value, department_value)

        # Получаем имя через get_display_name
        display_name = await get_display_name(
            self.user['telegram_id'],
            self.scene.__bot__
        )

        return self.content.format(
            telegram_id=self.user['telegram_id'],
            role=self.selected_role,
            tasker_id=self.user.get('tasker_id', 'Не привязан'),
            department=department_display,
            about=self.user.get('about', 'Не указано'),
            tasks=self.user.get('tasks', 0),
            tasks_year=self.user.get('task_per_year', 0),
            tasks_month=self.user.get('task_per_month', 0),
            name=display_name,
            created=self.user.get('tasks_created', 0),
            checked=self.user.get('tasks_checked', 0)
        )

    async def buttons_worker(self):
        user_id = self.scene.data['scene'].get('selected_user')
        current_user_telegram_id = self.scene.user_id

        # Проверяем, не редактирует ли админ себя
        is_self_edit = (user_id == current_user_telegram_id)
        is_admin = isinstance(self.user, dict) and (self.user.get('role') == 'admin')

        buttons = []

        if not is_self_edit or current_user_telegram_id == superuser_id:
            # Кнопки редактирования только если это не свой профиль
            buttons.extend([
                {
                    "text": "🎭 Изменить роль",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "select-role"
                    )
                },
                {
                    "text": "🏢 Изменить департамент",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "select-department"
                    )
                },
                {
                    "text": "📝 Изменить описание",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "edit-about"
                    )
                },
                {
                    "text": "❌ Удалить пользователя",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "delete-user"
                    ),
                    "ignore_row": True
                }
            ])
        else:
            # Для своего профиля показываем сообщение
            buttons.append({
                "text": "⚠️ Себя редактировать нельзя",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "self_edit_warning"
                ),
                "ignore_row": True
            })

        # Кнопка назад всегда доступна
        buttons.append({
            "text": "🔙 Назад",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "users-list"
            ),
            "ignore_row": True
        })
        
        return buttons
    
    @Page.on_callback('self_edit_warning')
    async def on_self_edit_warning(self, callback, args):
        await callback.answer("⚠️ Вы не можете редактировать свой профиль", show_alert=True)

    @Page.on_callback('delete-user')
    async def on_delete(self, callback, args):

        me_id = self.scene.user_id
        user_id = self.scene.data['scene'].get('selected_user')

        if user_id == me_id:
            await callback.answer("❌ Вы не можете удалить себя", show_alert=True)
            return

        await brain_client.delete_user(user_id)

        await callback.answer("✅ Пользователь удалён")
        await self.scene.update_page('users-list')

    @Page.on_callback('select-role')
    async def on_select_role(self, callback, args):
        await self.scene.update_key('scene', 'edit_mode', True)
        await self.scene.update_page('select-role')

    @Page.on_callback('select-department')
    async def on_select_department(self, callback, args):
        await self.scene.update_key('scene', 'edit_mode', True)
        await self.scene.update_page('select-department')

    @Page.on_callback('edit-about')
    async def on_edit_about(self, callback, args):
        await self.scene.update_key('scene', 'edit_mode', True)
        await self.scene.update_page('edit-about')

    @Page.on_callback('users-list')
    async def on_back(self, callback, args):
        await self.scene.update_page('users-list')

