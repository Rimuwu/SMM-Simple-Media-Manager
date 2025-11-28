from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import get_cards, brain_api, delete_scene
from global_modules.classes.enums import CardStatus, UserRole
from tg.scenes.edit.task_scene import TaskScene
from tg.oms.manager import scene_manager
from modules.api_client import get_user_role
from tg.oms import Scene


class TaskDetailPage(Page):
    __page_name__ = 'task-detail'

    async def data_preparate(self) -> None:
        # Загружаем детальную информацию о задаче
        role = self.scene.data['scene'].get('user_role')
        
        if role is None:
            telegram_id = self.scene.user_id
            user_role = await get_user_role(telegram_id)
            await self.scene.update_key('scene', 'user_role', user_role or None)

        await self.load_task_details()

    async def content_worker(self) -> str:
        return self.content

    async def load_task_details(self):
        """Загружает краткую информацию о выбранной задаче"""
        self.clear_content()
        
        task_id = self.scene.data['scene'].get('selected_task')
        if not task_id:
            return

        # Получаем информацию о задаче
        tasks = await get_cards(card_id=task_id)
        if not tasks:
            return
        
        task = tasks[0]
        
        # Форматируем статус
        status_names = {
            CardStatus.pass_: "⏳ Создано",
            CardStatus.edited: "✏️ В работе",
            CardStatus.review: "🔍 На проверке", 
            CardStatus.ready: "✅ Готова"
        }
        
        # Подготавливаем переменные для шаблона (только краткая информация)
        add_vars = {
            'task_name': task.get('name', 'Без названия'),
            'task_description': task.get('description', 'Нет описания'),
            'status': status_names.get(task.get('status'), task.get('status', 'Неизвестно'))
        }

        # Сохраняем данные задачи в сцену для использования в других методах
        await self.scene.update_key('scene', 'current_task_data', task)
        
        self.content = self.append_variables(**add_vars)

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()

        # Простые кнопки-заглушки для взаимодействия с задачей
        action_buttons = []

        role = self.scene.data['scene'].get('user_role')
        is_admin = role == UserRole.admin

        if role == UserRole.admin or is_admin:
            action_buttons.extend([
                ('assign_executor', '👷 Исполнитель'),
                ('delete', '🗑️ Удалить задачу'),
                ('change_deadline', '⏰ Изменить дедлайн')
            ])

        if role == UserRole.copywriter or is_admin:
            action_buttons.extend([
                ('open_task', '📂 Открыть задачу')
            ])

        if role == UserRole.editor or is_admin:
            action_buttons.extend([
                ('start_check', '🔎 Начать проверку')
            ])

        # Добавляем кнопки действий
        for action_key, action_name in action_buttons:
            result.append({
                'text': action_name,
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'task_action',
                    action_key
                )
            })

        return result

    @Page.on_callback('task_action')
    async def task_action_handler(self, callback, args):
        action = args[1]

        if action == 'open_task':
            selected_task = self.scene.data['scene'].get('selected_task')

            await self.scene.end()

            edit_scene: TaskScene = scene_manager.create_scene(
                self.scene.user_id, TaskScene, 
                self.scene.__bot__
            )
            edit_scene.set_taskid(selected_task)

            await edit_scene.start()
            return 'exit'

        elif action == 'delete':
            # Удаляем задачу
            task = self.scene.data['scene'].get('current_task_data')
            if not task:
                return

            card_id = task.get('card_id')
            if not card_id:
                return

            res, status = await brain_api.delete(
                f'/card/delete/{card_id}',
            )

            if status == 200:
                await self.scene.update_key(
                    'scene', 'selected_task', None)
                await self.scene.update_page('task-list')

                await callback.answer("Задача успешно удалена.", show_alert=True)

            else:
                await callback.answer("Ошибка при удалении задачи.", show_alert=True)