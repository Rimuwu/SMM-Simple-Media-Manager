"""
Страница выбора отдела для фильтрации задач (только для админов)
"""
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.classes.enums import Department
from tg.scenes.constants import DEPARTMENT_NAMES


class SelectDepartmentFilterPage(Page):
    __page_name__ = 'select-department-filter'

    async def data_preparate(self) -> None:
        pass

    async def content_worker(self) -> str:
        return "🏢 **Выберите отдел для фильтрации задач:**"

    async def buttons_worker(self) -> list[dict]:
        result = []
        
        # Используем enum Department
        for dept in Department:
            dept_key = dept.value
            dept_name = DEPARTMENT_NAMES.get(dept_key, dept_key)
            
            result.append({
                'text': f"🏢 {dept_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'sel_dept',
                    dept_key
                )
            })
        
        # Кнопка назад
        result.append({
            'text': '🔙 К фильтрам',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_fltr'
            ),
            'ignore_row': True
        })
        
        return result

    @Page.on_callback('sel_dept')
    async def select_department_handler(self, callback, args):
        department = args[1]
        
        # Сохраняем выбранный отдел и фильтр
        await self.scene.update_key('scene', 'selected_filter', 'by-department')
        await self.scene.update_key('scene', 'filter_department', department)
        await self.scene.update_key('scene', 'current_page', 0)
        
        # Переходим к списку задач
        await self.scene.update_page('task-list')

    @Page.on_callback('back_fltr')
    async def back_to_filters_handler(self, callback, args):
        await self.scene.update_page('filter-selection')
