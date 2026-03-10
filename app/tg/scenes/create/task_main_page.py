import copy
from datetime import datetime
from uuid import UUID as _UUID
from tg.oms import Page
from tg.oms.utils import callback_generator
from models.User import User
from modules.utils import get_user_display_name


class TaskMainPage(Page):
    """Главная страница задания — показывает название, описание, дедлайн и список постов."""

    __page_name__ = 'task-main'

    async def content_worker(self) -> str:
        task = self.scene.data.get('task', {})
        cards = self.scene.data.get('cards', [])

        name = task.get('name') or '➖'
        description = task.get('description') or '➖'

        deadline = task.get('deadline')
        if deadline:
            try:
                dt = datetime.fromisoformat(deadline)
                deadline_str = dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                deadline_str = deadline
        else:
            deadline_str = '➖'

        # Исполнитель
        executor_id = task.get('executor')
        executor_str = '➖'
        if executor_id:
            try:
                users = await User.find(user_id=_UUID(str(executor_id)))
                if users:
                    executor_str = get_user_display_name(users[0].to_dict())
                else:
                    executor_str = f'ID: {str(executor_id)[:8]}'
            except Exception:
                executor_str = f'ID: {str(executor_id)[:8]}'

        posts_list = ''
        for i, card in enumerate(cards, 1):
            posts_list += f'\n  {i}. `{card.get("name", "...")}`'

        if not posts_list:
            posts_list = '\n_Нет добавленных постов_'

        self.content = (
            f"📋 *Создание задания*\n\n"
            f"📌 Название: `{name}`\n"
            f"📄 Описание: `{description}`\n"
            f"📅 Дедлайн: {deadline_str}\n"
            f"👤 Исполнитель: {executor_str}\n\n"
            f"📮 *Посты в задании:*{posts_list}"
        )
        return self.content

    async def buttons_worker(self) -> list[dict]:
        task = self.scene.data.get('task', {})
        cards = self.scene.data.get('cards', [])

        buttons = [
            {
                'text': '📌 Название задания',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_task_name'),
            },
            {
                'text': '📄 Описание задания',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_task_description'),
            },
            {
                'text': '📅 Дедлайн задания',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_task_deadline'),
            },
            {
                'text': '👤 Исполнитель',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_task_executor'),
            },
            {
                'text': '➕ Добавить пост',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'add_post'),
                'ignore_row': True,
            },
        ]

        # Создать задание можно только если есть название и хотя бы один пост
        if task.get('name') and cards:
            buttons.append({
                'text': '✅ Создать задание',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_task_finish'),
                'ignore_row': True,
            })

        buttons.append({
            'text': '❌ Отменить',
            'callback_data': callback_generator(
                self.scene.__scene_name__, 'to_task_cancel'),
            'ignore_row': True,
        })

        return buttons

    @Page.on_callback('to_task_name')
    async def to_task_name(self, callback, args):
        await self.scene.update_page('task-name')

    @Page.on_callback('to_task_description')
    async def to_task_description(self, callback, args):
        await self.scene.update_page('task-description')

    @Page.on_callback('to_task_deadline')
    async def to_task_deadline(self, callback, args):
        await self.scene.update_page('task-deadline')

    @Page.on_callback('to_task_executor')
    async def to_task_executor(self, callback, args):
        await self.scene.update_page('task-executor')

    @Page.on_callback('add_post')
    async def add_post(self, callback, args):
        """Сбросить текущие данные карточки и перейти в редактор поста."""
        default = copy.deepcopy(self.scene.scene.standart_data)
        self.scene.data['scene'].update(default)
        await self.scene.save_to_db()
        await self.scene.update_page('main')

    @Page.on_callback('to_task_finish')
    async def to_task_finish(self, callback, args):
        await self.scene.update_page('finish')

    @Page.on_callback('to_task_cancel')
    async def to_task_cancel(self, callback, args):
        await self.scene.update_page('cancel')
