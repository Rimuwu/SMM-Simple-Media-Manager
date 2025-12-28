from tg.oms.models.radio_page import RadioTypeScene
from tg.oms.utils import callback_generator
from modules.api_client import get_users, get_kaiten_users_dict
from typing import Optional, Callable
from modules.utils import get_display_name

class UserSelectorPage(RadioTypeScene):
    """
    Базовый класс для страниц выбора пользователя/исполнителя.
    
    Загружает пользователей из БД и получает их имена:
    - Если у пользователя есть tasker_id - получает full_name из Kaiten
    - Если нет tasker_id - использует telegram_id как имя
    
    Attributes:
        update_to_db: Если True, обновляет данные через API после выбора
        allow_reset: Если True, показывает кнопку "Сбросить"
        on_success_callback: Опциональная функция для выполнения после успешного обновления
        filter_department: Если указан, фильтрует пользователей по департаменту
    """
    
    update_to_db: bool = False
    allow_reset: bool = True
    on_success_callback: Optional[Callable] = None
    filter_department: Optional[str] = None
    filter_roles: Optional[list[str]] = None

    users_data = []
    kaiten_users = {}

    # Количество пользователей на страницу (можно переопределить в дочернем классе)
    users_per_page: int = 8

    async def data_preparate(self):
        await super().data_preparate()

        if not self.users_data:
            # Получаем пользователей из БД с фильтром по департаменту если указан
            if self.filter_department:
                users = await get_users(department=self.filter_department)
            else:
                users = await get_users()
            
            if users:
                self.users_data = users
                
                # Получаем пользователей из Kaiten для тех, у кого есть tasker_id
                self.kaiten_users = await get_kaiten_users_dict()

        # Применяем фильтры (роли / департамент) и формируем список для пагинации
        filtered = []
        for user in self.users_data:
            if self.filter_department:
                user_department = user.get('department')
                if user_department != self.filter_department:
                    continue
            if self.filter_roles:
                user_role = user.get('role')
                if user_role not in self.filter_roles:
                    continue
            filtered.append(user)

        self.filtered_users = filtered

        # Инициализируем номер страницы в данных сцены
        page_key = f"{self.__page_name__}_page"
        current_page = self.scene.get_key(self.__page_name__, 'page')
        if current_page is None:
            # fallback to scene-level key
            current_page = self.scene.get_key('scene', page_key) or 0
            await self.scene.update_key(self.__page_name__, 'page', current_page)
            await self.scene.update_key('scene', page_key, current_page)

        # Формируем options только для текущей страницы
        page = self.scene.get_key(self.__page_name__, 'page') or 0
        start = page * self.users_per_page
        end = min(start + self.users_per_page, len(self.filtered_users))

        self.options = {}
        for user in self.filtered_users[start:end]:
            user_id = str(user['user_id'])
            display_name = await get_display_name(
                user['telegram_id'], 
                self.kaiten_users, 
                self.scene.__bot__, 
                user.get('tasker_id'),
                short=True
            )
            self.options[user_id] = display_name

    async def content_worker(self) -> str:
        """Формирует контент с отображением текущего пользователя"""
        current_user_id = self.scene.data['scene'].get(self.scene_key)
        current_user_name = 'Не назначен'
        
        if current_user_id:
            # Ищем пользователя в загруженных данных
            user_data = next((u for u in self.users_data if str(u.get('user_id')) == str(current_user_id)), None)
            if user_data:
                current_user_name = await get_display_name(
                    user_data['telegram_id'], 
                    self.kaiten_users, 
                    self.scene.__bot__, 
                    user_data.get('tasker_id')
                )
        
        # Формируем переменные для подстановки в шаблон
        variables = {
            'user': current_user_name,
            'executor': current_user_name
        }
        
        return self.append_variables(**variables)

    async def buttons_worker(self):
        buttons = await super().buttons_worker()

        # Навигация страниц
        page = self.scene.get_key(self.__page_name__, 'page') or 0
        total = len(self.filtered_users) if hasattr(self, 'filtered_users') else len(self.users_data)
        start = page * self.users_per_page
        end = min(start + self.users_per_page, total)

        # Добавляем индикатор страницы
        buttons.append({
            'text': f'📃 {start+1}-{end} из {total}',
            'callback_data': callback_generator(self.scene.__scene_name__, 'noop'),
            'ignore_row': True
        })

        nav_buttons = []
        if page > 0:
            nav_buttons.append({
                'text': '⬅️ Назад',
                'callback_data': callback_generator(self.scene.__scene_name__, 'usr_nav', str(page - 1)),
                'ignore_row': True
            })
        if end < total:
            nav_buttons.append({
                'text': 'Вперед ➡️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'usr_nav', str(page + 1)),
                'ignore_row': True
            })

        if nav_buttons:
            buttons.extend(nav_buttons)

        if self.allow_reset:
            buttons.append({
                'text': '❌ Сбросить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'reset_user'
                ),
                'next_line': True
            })

        return buttons

    @RadioTypeScene.on_callback('reset_user')
    async def reset_user(self, callback, args):
        """Сброс выбранного пользователя"""
        await self.scene.update_key('scene', self.scene_key, None)
        await self.scene.update_key(self.__page_name__, self.scene_key, None)
        
        # Если нужно обновить в БД
        if self.update_to_db:
            success = await self.update_to_database(None)
            
            if success:
                await callback.answer("✅ Пользователь сброшен")
            else:
                await callback.answer("❌ Ошибка при обновлении")
                return
        
        await self.scene.update_page(self.next_page)

    @RadioTypeScene.on_callback('usr_nav')
    async def user_page_nav_handler(self, callback, args):
        new_page = int(args[1])
        # Обновляем обе записи: и на уровне страницы, и в общей сцене (для совместимости)
        await self.scene.update_key(self.__page_name__, 'page', new_page)
        await self.scene.update_key('scene', f"{self.__page_name__}_page", new_page)
        await self.scene.update_message()

    async def on_selected(self, callback, selected_value):
        """Обработка выбора пользователя"""
        # Сохраняем в сцену
        await self.scene.update_key('scene', self.scene_key, selected_value)
        
        # Если нужно обновить в БД
        if self.update_to_db:
            success = await self.update_to_database(selected_value)
            
            if success:
                await callback.answer("✅ Пользователь назначен")
                
                # Выполняем callback если есть
                if self.on_success_callback:
                    await self.on_success_callback(callback, selected_value)
            else:
                await callback.answer("❌ Ошибка при обновлении")
                return
        
        # Переходим на следующую страницу
        await self.scene.update_page(self.next_page)
    
    async def update_to_database(self, user_id: Optional[str]) -> bool:
        """
        Метод для обновления данных в БД.
        Переопределяется в дочерних классах.
        """
        return True
