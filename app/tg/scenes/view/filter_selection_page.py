from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.enums import UserRole
from models.User import User

class FilterSelectionPage(Page):
    __page_name__ = 'filter-selection'

    async def data_preparate(self) -> None:
        # Убеждаемся, что роль пользователя загружена
        if not self.scene.data['scene'].get('user_role'):

            telegram_id = self.scene.user_id
            user_role = await User.role_for(telegram_id)
            await self.scene.update_key('scene', 'user_role', user_role or 'Не определена')

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()

        user_role = self.scene.data['scene'].get('user_role')

        # Фильтры в зависимости от роли
        if user_role == UserRole.admin:
            filters = [
                ('my-tasks', '📋 Мои задачи'),
                ('all-tasks', '📁 Все задачи'), 
                ('created-by-me', '➕ Созданные мной'),
                ('for-review', '✨ Требуют проверки'),
                ('by-user', '👤 По пользователю'),
                ('by-department', '🏢 По отделу')
            ]
        elif user_role == UserRole.copywriter:
            filters = [
                ('my-tasks', '📋 Мои задачи')
            ]
        elif user_role == UserRole.editor:
            filters = [
                ('my-tasks', '📋 Мои задачи'),
                ('for-review', '✨ Требуют проверки')
            ]
        elif user_role == UserRole.customer:
            filters = [
                ('created-by-me', '➕ Созданные мной'),
                ('department-tasks', '🏢 Задачи отдела')
            ]
        else:
            filters = []

        # Добавляем кнопки фильтров
        for filter_key, filter_name in filters:
            result.append({
                'text': filter_name,
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'select_filter', 
                    filter_key
                )
            })

        return result

    @Page.on_callback('select_filter')
    async def select_filter_handler(self, callback, args):
        filter_type = args[1]
        
        # Если выбран фильтр по пользователю - переходим на страницу выбора пользователя
        if filter_type == 'by-user':
            await self.scene.update_page('select-user-filter')
            return
        
        # Если выбран фильтр по отделу - переходим на страницу выбора отдела
        if filter_type == 'by-department':
            await self.scene.update_page('select-department-filter')
            return
        
        # Сохраняем выбранный фильтр и сбрасываем номер страницы
        await self.scene.update_key('scene', 'selected_filter', filter_type)
        await self.scene.update_key('scene', 'current_page', 0)
        
        # Переходим к списку задач
        await self.scene.update_page('task-list')
        await self.scene.update_message()