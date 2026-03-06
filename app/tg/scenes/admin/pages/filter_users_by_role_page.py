"""
Страница фильтрации пользователей по роли
"""
from tg.oms import Page
from tg.oms.utils import callback_generator
from tg.scenes.constants import ROLE_NAMES, ROLE_ICONS


class FilterUsersByRolePage(Page):
    __page_name__ = 'filter-users-by-role'

    async def content_worker(self) -> str:
        return "🎭 **Выберите роль для фильтрации:**"

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        for role_key, role_name in ROLE_NAMES.items():
            icon = ROLE_ICONS.get(role_key, '')
            buttons.append({
                "text": f"{icon} {role_name}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "set-role-filter",
                    role_key
                )
            })

        buttons.append({
            "text": "🔙 Назад",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "users-list"
            ),
            "ignore_row": True
        })

        return buttons

    @Page.on_callback('set-role-filter')
    async def on_set_role_filter(self, callback, args):
        role = args[1]
        await self.scene.update_key('scene', 'users_filter_role', role)
        await callback.answer(f"✅ Фильтр по роли установлен")
        await self.scene.update_page('users-list')

    @Page.on_callback('users-list')
    async def on_back(self, callback, args):
        await self.scene.update_page('users-list')
