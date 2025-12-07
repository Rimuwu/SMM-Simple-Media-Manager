"""
Страница выбора пользователя для фильтрации задач (только для админов)
"""
from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.brain_client import brain_client


class SelectUserFilterPage(Page):
    __page_name__ = 'select-user-filter'

    async def data_preparate(self) -> None:
        # Загружаем список всех пользователей
        users = await brain_client.get_users()
        await self.scene.update_key('scene', 'filter_users', users or [])
        await self.scene.update_key('scene', 'filter_user_page', 0)

    async def content_worker(self) -> str:
        return "👤 **Выберите пользователя для фильтрации задач:**"

    async def buttons_worker(self) -> list[dict]:
        result = []

        users = self.scene.data['scene'].get('filter_users', [])
        current_page = self.scene.data['scene'].get('filter_user_page', 0)
        kaiten_users = await brain_client.get_kaiten_users_dict()

        # По 8 пользователей на страницу
        users_per_page = 8
        start_index = current_page * users_per_page
        end_index = min(start_index + users_per_page, len(users))

        current_users = users[start_index:end_index]

        for idx, user in enumerate(current_users):
            # Получаем имя пользователя
            display_name = await get_display_name(
                user['telegram_id'], kaiten_users, self.scene.__bot__, 
                user.get('tasker_id')
            )

            # Используем индекс вместо UUID для сокращения callback_data
            user_index = start_index + idx
            
            result.append({
                'text': f"👤 {display_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'sel_usr',
                    str(user_index)
                )
            })
        
        # Навигация
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append({
                'text': '⬅️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'usr_nav',
                    str(current_page - 1)
                ),
                'ignore_row': True
            })
        
        if end_index < len(users):
            nav_buttons.append({
                'text': 'Вперед ➡️',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'usr_nav',
                    str(current_page + 1)
                ),
                'ignore_row': True
            })
        
        if nav_buttons:
            result.extend(nav_buttons)
        
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

    @Page.on_callback('sel_usr')
    async def select_user_handler(self, callback, args):
        user_index = int(args[1])
        
        # Получаем пользователя по индексу
        users = self.scene.data['scene'].get('filter_users', [])
        if user_index < len(users):
            user = users[user_index]
            user_id = user.get('user_id', '')
            
            # Сохраняем выбранного пользователя и фильтр
            await self.scene.update_key('scene', 'selected_filter', 'by-user')
            await self.scene.update_key('scene', 'filter_user_id', str(user_id))
            await self.scene.update_key('scene', 'current_page', 0)
            
            # Переходим к списку задач
            await self.scene.update_page('task-list')
        else:
            await callback.answer("❌ Пользователь не найден")

    @Page.on_callback('usr_nav')
    async def user_page_nav_handler(self, callback, args):
        new_page = int(args[1])
        await self.scene.update_key('scene', 'filter_user_page', new_page)
        await self.scene.update_message()

    @Page.on_callback('back_fltr')
    async def back_to_filters_handler(self, callback, args):
        await self.scene.update_page('filter-selection')
