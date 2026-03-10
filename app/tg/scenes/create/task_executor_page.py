from tg.oms.common_pages.user_selector_page import UserSelectorPage
from tg.oms import Page
from modules.utils import get_user_display_name


class TaskExecutorPage(UserSelectorPage):
    """Страница выбора исполнителя задания (сохраняет в task-данные)."""

    __page_name__ = 'task-executor'
    __scene_key__ = 'task_executor'  # внутренний ключ RadioTypeScene
    __next_page__ = 'task-main'

    update_to_db = False
    allow_reset = True
    filter_department = 'smm'

    async def on_selected(self, callback, selected_value):
        """Сохраняем выбранного исполнителя в scene.data['task']['executor']."""
        task = self.scene.data.get('task', {})
        task['executor'] = selected_value
        self.scene.data['task'] = task
        await self.scene.save_to_db()
        await self.scene.update_page(self.next_page)

    @Page.on_callback('reset_user')
    async def reset_user(self, callback, args):
        """Сброс исполнителя задания."""
        task = self.scene.data.get('task', {})
        task['executor'] = None
        self.scene.data['task'] = task
        await self.scene.save_to_db()
        await self.scene.update_page(self.next_page)

    async def content_worker(self) -> str:
        task = self.scene.data.get('task', {})
        current_executor_id = task.get('executor')
        current_user_name = 'Не назначен'

        if current_executor_id:
            user_data = next(
                (u for u in self.users_data if str(u.get('user_id')) == str(current_executor_id)),
                None,
            )
            if user_data:
                current_user_name = get_user_display_name(user_data)

        return (
            f"👤 *Выбор исполнителя задания*\n\n"
            f"Текущий исполнитель: *{current_user_name}*\n\n"
            f"Выберите нового исполнителя:"
        )
