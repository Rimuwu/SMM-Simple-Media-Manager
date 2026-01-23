"""
Страница фильтрации пользователей по отделу
"""
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.classes.enums import Department

# Маппинг отделов на читаемые имена
DEPARTMENT_NAMES = {
    Department.it.value: "IT отдел",
    Department.design.value: "Дизайн",
    Department.cosplay.value: "Косплей",
    Department.craft.value: "Крафт",
    Department.media.value: "Медиа",
    Department.board_games.value: "Настольные игры",
    Department.smm.value: "SMM",
    Department.judging.value: "Судейство",
    Department.streaming.value: "Твич",
    Department.without_department.value: "Без отдела",
}


class FilterUsersByDepartmentPage(Page):
    __page_name__ = 'filter-users-by-department'

    async def content_worker(self) -> str:
        return "🏢 **Выберите отдел для фильтрации:**"

    async def buttons_worker(self) -> list[dict]:
        buttons = []
        
        for dept in Department:
            dept_key = dept.value
            dept_name = DEPARTMENT_NAMES.get(dept_key, dept_key)
            
            buttons.append({
                "text": f"🏢 {dept_name}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "set_dept",
                    dept_key
                )
            })
        
        buttons.append({
            "text": "🔙 Назад",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "usr_list"
            ),
            "ignore_row": True
        })
        
        return buttons

    @Page.on_callback('set_dept')
    async def on_set_department_filter(self, callback, args):
        department = args[1]
        await self.scene.update_key('scene', 'users_filter_department', department)
        await callback.answer(f"✅ Фильтр по отделу установлен")
        await self.scene.update_page('users-list')

    @Page.on_callback('usr_list')
    async def on_back(self, callback, args):
        await self.scene.update_page('users-list')
