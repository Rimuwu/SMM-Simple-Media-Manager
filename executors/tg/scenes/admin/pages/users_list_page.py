from modules.utils import get_display_name
from tg.oms.common_pages.user_selector_page import UserSelectorPage
from global_modules.brain_client import brain_client
from tg.oms.utils import callback_generator
from global_modules.classes.enums import Department

# Маппинг отделов на читаемые имена
DEPARTMENT_NAMES = {
    Department.it.value: "IT",
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


class UsersListPage(UserSelectorPage):
    __page_name__ = 'users-list'
    __next_page__ = 'user-detail'
    __select_icon__ = ''
    allow_reset = False

    async def data_preparate(self) -> None:
        # Инициализируем фильтры если их нет
        if 'users_filter_role' not in self.scene.data['scene']:
            await self.scene.update_key('scene', 'users_filter_role', None)

        if 'users_filter_department' not in self.scene.data['scene']:
            await self.scene.update_key('scene', 'users_filter_department', None)

        # Получаем фильтры из сцены
        filter_role = self.scene.data['scene'].get('users_filter_role')
        filter_department = self.scene.data['scene'].get('users_filter_department')

        # Получаем всех пользователей через brain_client — фильтрацию выполняет базовый класс `UserSelectorPage`
        users = await brain_client.get_users()

        self.users_data = users or []
        self.kaiten_users = await brain_client.get_kaiten_users_dict()

        # Передаём фильтры в базовый селектор
        self.filter_department = filter_department
        self.filter_roles = [filter_role] if filter_role else None
        # Кол-во пользователей на странице — используем для совместимости и для RadioTypeScene
        self.users_per_page = 8
        self.max_on_page = 8

        # Используем логику родителя для фильтрации и формирования options
        await super().data_preparate()

        # Подставляем иконки ролей перед именем в опциях (чтобы сохранить прежний вид)
        roles_icons = {
            'admin': '👑',
            'customer': '🎩',
            'copywriter': '👤',
            'editor': '🖋️'
        }

        # self.options сформированы как {user_id: display_name}
        for uid in list(self.options.keys()):
            user = next((u for u in self.filtered_users if str(u.get('user_id')) == uid), None)
            if user:
                role_icon = roles_icons.get(user.get('role', ''), '👤')
                self.options[uid] = f"{role_icon} {self.options[uid]}"

    async def content_worker(self) -> str:
        filter_role = self.scene.data['scene'].get('users_filter_role')
        filter_department = self.scene.data['scene'].get('users_filter_department')

        # Маппинги для отображения
        role_names = {
            'admin': 'Админы',
            'customer': 'Заказчики',
            'copywriter': 'Копирайтеры',
            'editor': 'Редакторы'
        }

        filter_text = ""
        if filter_role:
            filter_text += f"\n🎭 Роль: *{role_names.get(filter_role, filter_role)}*"
        if filter_department:
            filter_text += f"\n🏢 Отдел: *{DEPARTMENT_NAMES.get(filter_department, filter_department)}*"

        if filter_text:
            return f"👥 **Управление пользователями**{filter_text}\n\nВыберите пользователя для редактирования или добавьте нового."
        else:
            return "👥 **Управление пользователями**\n\nВыберите пользователя для редактирования или добавьте нового."

    async def buttons_worker(self) -> list[dict]:
        # Базовые кнопки от UserSelectorPage (опции пользователей + навигация + сброс выбранного)
        buttons = await super().buttons_worker()

        filter_role = self.scene.data['scene'].get('users_filter_role')
        filter_department = self.scene.data['scene'].get('users_filter_department')

        # Кнопки фильтрации
        buttons.append({
            "text": "🎭 По роли",
            "callback_data": callback_generator(self.scene.__scene_name__, "filter-by-role"),
            "next_line": True
        })

        buttons.append({
            "text": "🏢 По отделу",
            "callback_data": callback_generator(self.scene.__scene_name__, "filter-by-department"),
        })

        # Кнопка сброса фильтров (если есть фильтры)
        if filter_role or filter_department:
            buttons.append({
                "text": "🔄 Сбросить фильтры",
                "callback_data": callback_generator(self.scene.__scene_name__, "reset-filters"),
                "ignore_row": True
            })

        buttons.append({
            "text": "➕ Добавить пользователя",
            "callback_data": callback_generator(self.scene.__scene_name__, "add-user"),
            "ignore_row": True
        })

        return buttons

    @UserSelectorPage.on_callback('filter-by-role')
    async def on_filter_by_role(self, callback, args):
        await self.scene.update_page('filter-users-by-role')

    @UserSelectorPage.on_callback('filter-by-department')
    async def on_filter_by_department(self, callback, args):
        await self.scene.update_page('filter-users-by-department')

    @UserSelectorPage.on_callback('reset-filters')
    async def on_reset_filters(self, callback, args):
        await self.scene.update_key('scene', 'users_filter_role', None)
        await self.scene.update_key('scene', 'users_filter_department', None)
        await callback.answer("✅ Фильтры сброшены")
        await self.scene.update_message()

    @UserSelectorPage.on_callback('add-user')
    async def on_add_user(self, callback, args):
        # Сбрасываем все данные нового пользователя
        self.scene.data['scene'].update(
            {
                'new_user_id': None,
                'new_user_role': None,
                'new_user_tasker_id': None,
                'new_user_department': None,
                'about_text': '',
                'selected_role': None,
                'selected_kaiten_id': None,
                'selected_department': None
            }
        )
        self.scene.data['edit-about']['about_text'] = ''
        self.scene.data['select-department']['selected_department'] = None
        self.scene.data['select-kaiten-user']['selected_kaiten_id'] = None
        self.scene.data['select-role']['selected_role'] = None

        await self.scene.save_to_db()
        await self.scene.update_page('add-user')

    async def on_selected(self, callback, selected_value):
        """При выборе пользователя — переходим на страницу деталей пользователя"""
        # selected_value — это user_id; находим telegram_id для совместимости с остальным кодом
        user = next((u for u in self.users_data if str(u.get('user_id')) == str(selected_value)), None)
        if user and user.get('telegram_id'):
            telegram_id = int(user['telegram_id'])
        else:
            # fallback — используем переданное значение
            telegram_id = int(selected_value)

        await self.scene.update_key('scene', 'selected_user', telegram_id)
        await self.scene.update_page(self.__next_page__)

