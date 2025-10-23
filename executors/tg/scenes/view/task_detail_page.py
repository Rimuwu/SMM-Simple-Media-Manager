from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import get_cards, brain_api
from global_modules.classes.enums import CardStatus

class TaskDetailPage(Page):
    __page_name__ = 'task-detail'

    async def data_preparate(self) -> None:
        # Загружаем детальную информацию о задаче
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
            CardStatus.pass_: "⏳ Назначена",
            CardStatus.edited: "✏️ Отредактирована",
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
        action_buttons = [
            ('edit_task', '✏️ Редактировать'),
            ('change_status', '🔄 Изменить статус'),
            ('assign_executor', '� Назначить исполнителя'),
            ('add_comment', '💬 Добавить комментарий'),
            ('view_history', '📋 История изменений')
        ]
        
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
        action = args[0]
        
        # Заглушки для действий с задачами
        action_messages = {
            'edit_task': '✏️ Редактирование задачи (в разработке)',
            'change_status': '� Изменение статуса (в разработке)',
            'assign_executor': '👤 Назначение исполнителя (в разработке)',
            'add_comment': '💬 Добавление комментария (в разработке)',
            'view_history': '📋 История изменений (в разработке)'
        }
        
        message = action_messages.get(action, 'Функция в разработке')
        
        # Показываем уведомление с информацией о заглушке
        await callback.answer(message, show_alert=True)