"""
Страница выбора пользователя для фильтрации задач (только для админов)
"""
from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.brain_client import brain_client
from tg.oms.common_pages.user_selector_page import UserSelectorPage


class SelectUserFilterPage(UserSelectorPage):
    __page_name__ = 'select-user-filter'
    # Указываем ключ сцены, в который будет сохранён выбранный пользователь
    __scene_key__ = 'filter_user_id'
    # После выбора переходим к списку задач
    __next_page__ = 'task-list'
    # Не показываем кнопку сброса в этом селекторе
    allow_reset = True

    async def content_worker(self) -> str:
        return "👤 **Выберите пользователя для фильтрации задач:**"

    async def on_selected(self, callback, selected_value):
        # Сохраняем выбранный фильтр и сбрасываем страницу списка
        await self.scene.update_key('scene', 'selected_filter', 'by-user')
        await self.scene.update_key('scene', 'current_page', 0)
        # Дальше выполняем стандартное поведение (переход на next_page)
        await super().on_selected(callback, selected_value)

    @Page.on_callback('back_fltr')
    async def back_to_filters_handler(self, callback, args):
        await self.scene.update_page('filter-selection')
