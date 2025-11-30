from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import get_cards, get_users
from global_modules.classes.enums import UserRole, CardStatus

filter_names = {
    'my-tasks': 'Мои задачи',
    'all-tasks': 'Все задачи',
    'created-by-me': 'Созданные мной',
    'for-review': 'Проверяемые мной'
}

class TaskListPage(Page):
    __page_name__ = 'task-list'

    async def data_preparate(self) -> None:

        selected_filter = self.scene.data['scene'].get('selected_filter')

        if selected_filter is None:
            user_role = self.scene.data['scene'].get('user_role')

            if user_role == UserRole.admin:
                selected_filter = 'all-tasks'
            elif user_role == UserRole.copywriter:
                selected_filter = 'my-tasks'
            elif user_role == UserRole.editor:
                selected_filter = 'for-review'
            elif user_role == UserRole.customer:
                selected_filter = 'created-by-me'
            else:
                selected_filter = 'my-tasks'  # Общий фильтр по умолчанию

            await self.scene.update_key('scene',    
                        'selected_filter', selected_filter)

        # Загружаем задачи в зависимости от выбранного фильтра
        await self.load_tasks()

    async def content_worker(self) -> str:
        self.clear_content()

        tasks = self.scene.data['scene'].get(
            'tasks', []
        )
        selected_filter = self.scene.data['scene'].get(
            'selected_filter', ''
        )
        current_page = self.scene.data['scene'].get(
            'current_page', 0
        )

        # Показываем по 5 задач на страницу
        tasks_per_page = 5
        total_tasks = len(tasks)
        start_index = current_page * tasks_per_page
        end_index = min(start_index + tasks_per_page, total_tasks)

        add_vars = {
            'selected_filter': filter_names.get(selected_filter, selected_filter),
            'current_range': f"{start_index + 1}-{end_index}",
            'total_tasks': str(total_tasks)
        }

        self.content = self.append_variables(**add_vars)
        return self.content

    async def load_tasks(self):
        """Загружает задачи в зависимости от фильтра и роли пользователя"""
        telegram_id = self.scene.user_id
        selected_filter = self.scene.data['scene'].get('selected_filter')
        
        # Получаем информацию о пользователе
        users = await get_users(telegram_id=telegram_id)
        if not users:
            await self.scene.update_key('scene', 'tasks', [])
            print(f"Failed to load user info for telegram_id {telegram_id}")
            return

        user = users[0]
        user_uuid = user['user_id']
        
        # Загружаем задачи в зависимости от фильтра
        tasks = []

        if selected_filter == 'my-tasks':
            # Задачи где пользователь исполнитель
            tasks = await get_cards(executor_id=user_uuid)

        elif selected_filter == 'all-tasks':
            # Все задачи (только для админа)
            tasks = await get_cards()

        elif selected_filter == 'created-by-me':
            # Задачи созданные пользователем
            tasks = await get_cards(customer_id=user_uuid)
        elif selected_filter == 'for-review':
            # Задачи на проверку
            tasks = await get_cards(status=CardStatus.review)

        await self.scene.update_key('scene', 'tasks', tasks)

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()
        
        tasks = self.scene.data['scene'].get('tasks', [])
        current_page = self.scene.data['scene'].get('current_page', 0)
        
        # Показываем по 5 задач на страницу
        tasks_per_page = 5
        start_index = current_page * tasks_per_page
        end_index = min(start_index + tasks_per_page, len(tasks))
        
        # Добавляем кнопки для задач на текущей странице
        current_tasks = tasks[start_index:end_index]
        
        for i, task in enumerate(current_tasks):
            task_name = task.get('name', 'Без названия')
            if len(task_name) > 30:
                task_name = task_name[:30] + "..."
            
            result.append({
                'text': f"📝 {task_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'view_task',
                    str(task.get('card_id', ''))
                )
            })
        
        # Навигация по страницам
        nav_buttons = []
        
        # Предыдущая страница
        if current_page > 0:
            nav_buttons.append({
                'text': '⬅️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'page_nav', 
                    str(current_page - 1)
                ),
                "ignore_row": True
            })
        
        # Следующая страница
        if end_index < len(tasks):
            nav_buttons.append({
                'text': 'Вперед ➡️',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'page_nav', 
                    str(current_page + 1)
                ),
                "ignore_row": True
            })
        
        # Добавляем навигационные кнопки в новой строке
        if nav_buttons:
            result.extend(nav_buttons)

        return result

    @Page.on_callback('view_task')
    async def view_task_handler(self, callback, args):
        task_id = args[1]
        
        # Сохраняем ID выбранной задачи
        await self.scene.update_key('scene', 'selected_task', task_id)
        
        # Переходим к детальному просмотру
        await self.scene.update_page('task-detail')
        await self.scene.update_message()

    @Page.on_callback('page_nav')
    async def page_nav_handler(self, callback, args):
        new_page = int(args[1])
        
        # Обновляем номер текущей страницы
        await self.scene.update_key('scene', 'current_page', new_page)
        
        # Перезагружаем сообщение
        await self.scene.update_message()