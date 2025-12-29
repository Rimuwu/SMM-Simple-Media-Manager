from modules.utils import get_display_name
from tg.oms import Page
from global_modules.brain_client import brain_client
from tg.oms.utils import callback_generator
from global_modules.classes.enums import Department

# Маппинг отделов на читаемые имена
DEPARTMENT_NAMES = {
    Department.it.value: "IT отдел",
    Department.design.value: "Дизайн",
    Department.cosplay.value: "Косплей",
    Department.craft.value: "Ремесло",
    Department.media.value: "Медиа",
    Department.board_games.value: "Настольные игры",
    Department.smm.value: "SMM",
    Department.judging.value: "Судейство",
    Department.streaming.value: "Стриминг",
    Department.without_department.value: "Без отдела",
}


class UsersListPage(Page):
    __page_name__ = 'users-list'

    async def data_preparate(self) -> None:
        # Инициализируем фильтры если их нет
        if 'users_filter_role' not in self.scene.data['scene']:
            await self.scene.update_key('scene', 
                    'users_filter_role', None)

        if 'users_filter_department' not in self.scene.data['scene']:
            await self.scene.update_key('scene', 
                    'users_filter_department', None)

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
        filter_role = self.scene.data['scene'].get('users_filter_role')
        filter_department = self.scene.data['scene'].get('users_filter_department')
        
        # Получаем пользователей с фильтрами
        if filter_role and filter_department:
            users = await brain_client.get_users(role=filter_role, department=filter_department)
        elif filter_role:
            users = await brain_client.get_users(role=filter_role)
        elif filter_department:
            users = await brain_client.get_users(department=filter_department)
        else:
            users = await brain_client.get_users()
        
        buttons = []
        
        roles = {
            'admin': '👑',
            'customer': '🎩',
            'copywriter': '👤',
            'editor': '🖋️'
        }

        kaiten_users_dict = await brain_client.get_kaiten_users_dict()
        
        for user in users:
            if not isinstance(user, dict):
                continue
            role_icon = roles.get(user.get('role', ''), "👤")

            name = await get_display_name(
                user['telegram_id'], kaiten_users_dict, self.scene.__bot__, user.get('tasker_id')
            )
            buttons.append({
                "text": f"{role_icon} {name}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "user-detail",
                    str(user.get('telegram_id', ''))
                )
            })
        
        # Кнопки фильтрации
        buttons.append({
            "text": "🎭 Фильтр по роли",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "filter-by-role"
            ),
            "ignore_row": True
        })
        
        buttons.append({
            "text": "🏢 Фильтр по отделу",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "filter-by-department"
            ),
            "ignore_row": True
        })
        
        # Кнопка сброса фильтров (если есть фильтры)
        if filter_role or filter_department:
            buttons.append({
                "text": "🔄 Сбросить фильтры",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "reset-filters"
                ),
                "ignore_row": True
            })
            
        buttons.append({
            "text": "➕ Добавить пользователя",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "add-user"
            ),
            "ignore_row": True
        })

        return buttons

    @Page.on_callback('user-detail')
    async def on_user_detail(self, callback, args):
        telegram_id = int(args[1])

        await self.scene.update_key('scene', 
                                    'selected_user', telegram_id)
        await self.scene.update_page('user-detail')

    @Page.on_callback('filter-by-role')
    async def on_filter_by_role(self, callback, args):
        await self.scene.update_page('filter-users-by-role')

    @Page.on_callback('filter-by-department')
    async def on_filter_by_department(self, callback, args):
        await self.scene.update_page('filter-users-by-department')

    @Page.on_callback('reset-filters')
    async def on_reset_filters(self, callback, args):
        await self.scene.update_key('scene', 
                                    'users_filter_role', None)
        await self.scene.update_key('scene', 
                                    'users_filter_department', None)
        await callback.answer("✅ Фильтры сброшены")
        await self.scene.update_message()

    @Page.on_callback('add-user')
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
        self.scene.data['edit-about'][
            'about_text'] = ''
        self.scene.data['select-department'][
            'selected_department'] = None
        self.scene.data['select-kaiten-user'][
            'selected_kaiten_id'] = None
        self.scene.data['select-role'][
            'selected_role'] = None

        await self.scene.save_to_db()
        await self.scene.update_page('add-user')

