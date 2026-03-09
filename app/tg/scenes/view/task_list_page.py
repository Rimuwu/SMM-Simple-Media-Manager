from datetime import datetime, timedelta
from tg.oms import Page
from tg.oms.utils import callback_generator
from models.Card import Card
from models.User import User
from uuid import UUID as _UUID
from modules.enums import UserRole, CardStatus, Department
from modules.utils import get_user_display_name
from tg.scenes.constants import DEPARTMENT_NAMES

filter_names = {
    'my-tasks': 'Мои задачи',
    'all-tasks': 'Все задачи',
    'created-by-me': 'Созданные мной',
    'for-review': 'Проверяемые мной',
    'department-tasks': 'Задачи отдела',
    'by-user': 'По пользователю',
    'by-department': 'По отделу'
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

        # Формируем текст фильтра с дополнительной информацией
        selected_filter_text = filter_names.get(selected_filter, selected_filter)

        if selected_filter == 'by-user':
            filter_user_id = self.scene.data['scene'].get('filter_user_id')
            if filter_user_id:
                user = await User.get_by_id(_UUID(str(filter_user_id)))
                if user:
                    selected_filter_text = f"{filter_names.get(selected_filter)}: {get_user_display_name(user)}"
                else:
                    selected_filter_text = f"{filter_names.get(selected_filter)}: ID {filter_user_id}"
            else:
                selected_filter_text = f"{filter_names.get(selected_filter)}: —"

        elif selected_filter == 'by-department':
            filter_department = self.scene.data['scene'].get('filter_department')
            if filter_department:
                department_name = DEPARTMENT_NAMES.get(filter_department, filter_department)
                selected_filter_text = f"{filter_names.get(selected_filter)}: {department_name}"

        add_vars = {
            'selected_filter': selected_filter_text,
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
        users = await User.find(telegram_id=telegram_id)
        if not users:
            await self.scene.update_key('scene', 'tasks', [])
            print(f"Failed to load user info for telegram_id {telegram_id}")
            return

        user = users[0]
        user_uuid = user.user_id
        
        # Загружаем задачи в зависимости от фильтра
        tasks = []

        if selected_filter == 'my-tasks':
            # Задачи где пользователь исполнитель
            tasks = [c.to_dict() for c in await Card.find(executor_id=user_uuid)]

        elif selected_filter == 'all-tasks':
            # Все задачи (только для админа)
            tasks = [c.to_dict() for c in await Card.find()]

        elif selected_filter == 'created-by-me':
            # Задачи созданные пользователем
            tasks = [c.to_dict() for c in await Card.find(customer_id=user_uuid)]

        elif selected_filter == 'for-review':
            # Задачи на проверку
            tasks = [c.to_dict() for c in await Card.find(status=CardStatus.review)]

        elif selected_filter == 'department-tasks':
            # Задачи отдела - получаем всех пользователей из отдела и их задачи
            department = user.department
            if department:
                # Получаем всех пользователей из этого отдела
                department_users = await User.find(department=department)
                # Собираем все задачи этих пользователей
                all_department_tasks = []
                for dept_user in department_users:
                    dept_user_id = dept_user.user_id
                    # Получаем задачи где пользователь исполнитель
                    all_department_tasks.extend(c.to_dict() for c in await Card.find(executor_id=dept_user_id))
                    # Получаем задачи созданные пользователем
                    all_department_tasks.extend(c.to_dict() for c in await Card.find(customer_id=dept_user_id))

                # Убираем дубликаты по card_id
                seen_ids = set()
                tasks = []
                for task in all_department_tasks:
                    task_id = task.get('card_id')
                    if task_id not in seen_ids:
                        seen_ids.add(task_id)
                        tasks.append(task)
            else:
                tasks = []

        elif selected_filter == 'by-user':
            # Задачи конкретного пользователя (для админов)
            filter_user_id = self.scene.data['scene'].get('filter_user_id')
            if filter_user_id:
                # Получаем задачи где пользователь исполнитель
                executor_tasks = [c.to_dict() for c in await Card.find(executor_id=filter_user_id)]
                # Получаем задачи созданные пользователем
                customer_tasks = [c.to_dict() for c in await Card.find(customer_id=filter_user_id)]

                # Объединяем и убираем дубликаты
                all_tasks = executor_tasks + customer_tasks
                seen_ids = set()
                tasks = []
                for task in all_tasks:
                    task_id = task.get('card_id')
                    if task_id not in seen_ids:
                        seen_ids.add(task_id)
                        tasks.append(task)
            else:
                tasks = []

        elif selected_filter == 'by-department':
            # Задачи по отделу (для админов)
            filter_department = self.scene.data['scene'].get('filter_department')
            if filter_department:
                # Получаем всех пользователей из отдела
                department_users = await User.find(department=filter_department)

                all_department_tasks = []
                for dept_user in department_users:
                    dept_user_id = dept_user.user_id
                    all_department_tasks.extend(c.to_dict() for c in await Card.find(executor_id=dept_user_id))
                    all_department_tasks.extend(c.to_dict() for c in await Card.find(customer_id=dept_user_id))

                # Убираем дубликаты
                seen_ids = set()
                tasks = []
                for task in all_department_tasks:
                    task_id = task.get('card_id')
                    if task_id not in seen_ids:
                        seen_ids.add(task_id)
                        tasks.append(task)
            else:
                tasks = []

        await self.scene.update_key('scene', 'tasks', tasks)

    def sort_tasks_by_deadline(self, tasks: list) -> list:
        """Сортирует задачи по дедлайну (ближайшие первые)"""
        def get_deadline_sort_key(task):
            deadline = task.get('deadline')
            if deadline:
                try:
                    if isinstance(deadline, str):
                        return datetime.fromisoformat(deadline)
                    return deadline
                except:
                    pass
            # Задачи без дедлайна в конец
            return datetime.max

        return sorted(tasks, key=get_deadline_sort_key)

    def format_deadline_label(self, task: dict) -> str:
        """Форматирует название задачи с дедлайном и эмодзи"""
        task_name = task.get('name', 'Без названия')
        if len(task_name) > 25:
            task_name = task_name[:25] + "..."
        
        deadline = task.get('deadline')
        deadline_str = ""
        urgent_emoji = "📝"
        
        if deadline:
            try:
                if isinstance(deadline, str):
                    dt = datetime.fromisoformat(deadline)
                else:
                    dt = deadline
                
                # Форматируем дату
                deadline_str = f" ({dt.strftime('%d.%m')})"
                
                # Проверяем, меньше ли дня до дедлайна
                now = datetime.now()
                time_left = dt - now
                
                if time_left < timedelta(days=1):
                    urgent_emoji = "🔴"
                elif time_left < timedelta(days=2):
                    urgent_emoji = "🟠"
            except:
                pass
        
        return f"{urgent_emoji} {task_name}{deadline_str}"

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()
        
        tasks = self.scene.data['scene'].get('tasks', [])
        current_page = self.scene.data['scene'].get('current_page', 0)
        
        # Сортируем задачи по дедлайну
        tasks = self.sort_tasks_by_deadline(tasks)
        
        # Показываем по 5 задач на страницу
        tasks_per_page = 5
        start_index = current_page * tasks_per_page
        end_index = min(start_index + tasks_per_page, len(tasks))
        
        # Добавляем кнопки для задач на текущей странице
        current_tasks = tasks[start_index:end_index]
        
        for i, task in enumerate(current_tasks):
            # Используем новый формат с дедлайном и эмодзи
            button_text = self.format_deadline_label(task)
            
            result.append({
                'text': button_text,
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'view_task',
                    str(task.get('card_id', ''))
                ),
                "ignore_row": True
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
                "ignore_row": False
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
                "ignore_row": False
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
        # await self.scene.update_message()

    @Page.on_callback('page_nav')
    async def page_nav_handler(self, callback, args):
        new_page = int(args[1])
        
        # Обновляем номер текущей страницы
        await self.scene.update_key('scene', 'current_page', new_page)
        
        # Перезагружаем сообщение
        await self.scene.update_message()
