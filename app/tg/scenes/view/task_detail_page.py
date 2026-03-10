from modules.utils import get_user_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from app.models.card.Card import Card
from models.User import User
from modules.card import card_service
from modules.enums import CardStatus, UserRole
from tg.scenes.edit.task_scene import TaskScene
from tg.oms.manager import scene_manager
from modules.logs import logger
from modules.card import card_events
from uuid import UUID as _UUID
from datetime import datetime
from tg.scenes.constants import CARD_STATUS_NAMES, format_channels, format_tags


class TaskDetailPage(Page):
    __page_name__ = 'task-detail'

    async def data_preparate(self) -> None:
        # Загружаем детальную информацию о задаче
        role = self.scene.data['scene'].get('user_role')
        self.user = None

        telegram_id = self.scene.user_id
        user = await User.by_telegram(telegram_id)
        if user:
            self.user = user
            if role is None:
                await self.scene.update_key('scene', 'user_role', user.role.value)

        await self.load_task_details()

    async def load_task_details(self):
        """Загружает краткую информацию о выбранной задаче"""
        self.clear_content()

        task_id = self.scene.data['scene'].get('selected_task')
        if not task_id:
            return

        # Получаем информацию о задаче
        tasks = await Card.find(card_id=task_id)
        if not tasks:
            return

        task = tasks[0]

        # Форматируем исполнителя
        executor_id = task.executor_id
        executor_name = 'Не назначен'
        if executor_id:
            user_data = await User.get_by_id(_UUID(str(executor_id)))
            if user_data:
                executor_name = get_user_display_name(user_data)

        # Форматируем заказчика
        customer_id = task.customer_id
        customer_name = 'Не указан'
        if customer_id:
            user_data = await User.get_by_id(_UUID(str(customer_id)))
            if user_data:
                customer_name = get_user_display_name(user_data)

        # Форматируем редактора
        editor_id = task.editor_id
        editor_name = 'Не указан'
        if editor_id:
            user_data = await User.get_by_id(_UUID(str(editor_id)))
            if user_data:
                editor_name = get_user_display_name(user_data)

        # Форматируем дедлайн
        deadline = task.deadline
        if deadline:
            try:
                deadline_str = deadline.strftime('%d.%m.%Y %H:%M')
            except:
                deadline_str = str(deadline)
        else:
            deadline_str = 'Не установлен'

        # Форматируем даты отправки
        send_time = task.send_time
        if send_time:
            try:
                send_time_str = send_time.strftime('%d.%m.%Y %H:%M')
            except:
                send_time_str = str(send_time)
        else:
            send_time_str = 'Не установлено'

        # Форматируем каналы
        channels_str = format_channels(task.clients or [])

        # Форматируем теги (асинхронно, с учетом порядка)
        tags_str = await format_tags(task.tags or [])

        task_status_val = task.status.value if hasattr(task.status, 'value') else task.status
        add_vars = {
            'task_name': task.name or 'Без названия',
            'task_description': task.description or 'Нет описания',
            'status': CARD_STATUS_NAMES.get(task_status_val, task_status_val or 'Неизвестно'),
            'executor': executor_name,
            'customer': customer_name,
            'editor': editor_name,
            'deadline': deadline_str,
            'channels': channels_str,
            'tags': tags_str,
            'send_time': send_time_str
        }

        await self.scene.update_key('scene', 'current_task_data', task.to_dict())

        self.content = self.append_variables(**add_vars)
        self.content = self.content.replace('None', '➖')

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()

        # Простые кнопки-заглушки для взаимодействия с задачей
        action_buttons = []

        # Кнопки для статуса Ready (Админы и Редакторы)
        current_task = self.scene.data['scene'].get('current_task_data', {})
        task_status = current_task.get('status')

        role = self.scene.data['scene'].get('user_role')
        editor_id = current_task.get('editor_id')
        user_id = str(self.user.user_id) if self.user else None

        is_editor = str(current_task.get('editor_id', 0)) == user_id
        is_executor = str(current_task.get('executor_id', 0)) == user_id
        is_admin = role == UserRole.admin

        if is_executor or is_admin or is_editor:
            action_buttons.extend([
                ('open_task', '📂 Открыть задачу', 'primary')
            ])

        if is_admin:
            action_buttons.extend([
                ('assign_executor', '👷 Исполнитель')
            ])

        if editor_id is None:
            if role == UserRole.editor or is_admin:
                action_buttons.extend([
                ('set_editor', '💡 Стать редактором')
            ])

        # Если задача отправлена (sent), то для всех кроме админа кнопок нет (или только выход)
        if task_status == CardStatus.sent:
            if is_admin:
                return [{
                    'text': '🗑️ Удалить задачу',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__, 
                        'task_action',
                        'delete'
                    )},
                    {
                    'text': '↩️ Вернуть в работу',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__, 
                        'task_action',
                        'return_to_work',
                    )}
                ]
            else:
                return [] # Пустой список кнопок (только "Назад" от сцены если есть)

        if (is_admin or role == UserRole.editor or is_executor) and task_status == CardStatus.ready:
             # Проверяем, нет ли уже этой кнопки (чтобы не дублировать для админа/редактора, который может быть и исполнителем)
             if not any(b[0] == 'return_to_work' for b in action_buttons):
                 action_buttons.extend([
                    ('return_to_work', '↩️ Вернуть в работу')
                ])

        if (is_admin or role == UserRole.editor) and task_status == CardStatus.ready:
             if not any(b[0] == 'send_now' for b in action_buttons):
                 action_buttons.extend([
                    ('send_now', '🚀 Отправить сейчас')
                ])

        if role == UserRole.customer or is_admin:
            if is_admin:
                # Только админ может изменять название и описание
                action_buttons.extend([
                    ('change_name', '✏️ Изменить название')
                ])
            action_buttons.extend([
                ('change_deadline', '⏰ Изменить дедлайн'),
                ('contact', '📬 Связь'),
                ('files-view', '📁 Файлы'),
                ('delete', '🗑️ Удалить задачу', 'danger'),
                ('change_description', '📝 Изменить описание')
            ])

            if task_status in [CardStatus.review, CardStatus.ready]:
                action_buttons.extend([
                    ('preview', '👁 Просмотреть пост')
                ])

        # Добавляем кнопки действий
        for action in action_buttons:
            if len(action) != 3: action = (*action, None)
            action_key, action_name, style = action

            result.append({
                'text': action_name,
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 
                    'task_action',
                    action_key
                ),
                'style': style
            })

        return result

    @Page.on_callback('task_action')
    async def task_action_handler(self, callback, args):
        action = args[1]

        if action == 'assign_executor':
            # Переход на страницу назначения исполнителя
            await self.scene.update_page('assign-executor')
            return
        
        elif action == 'change_name':
            # Переход на страницу изменения названия
            await self.scene.update_page('change-name')
            return
        
        elif action == 'change_description':
            # Переход на страницу изменения описания
            await self.scene.update_page('change-description')
            return
        
        elif action == 'change_deadline':
            # Переход на страницу изменения дедлайна
            await self.scene.update_page('change-deadline')
            return

        elif action == 'preview':
            # Переход на страницу предпросмотра поста
            await self.scene.update_page('post-preview')
            return

        elif action == 'files-view':
            # Переход на страницу просмотра файлов
            await self.scene.update_page('files-view')
            return

        elif action == 'contact':
            # Переход на страницу связи с участниками
            await self.scene.update_page('contact')
            return

        elif action == 'open_task':
            selected_task = self.scene.data['scene'].get('selected_task')

            await self.scene.end()

            edit_scene: TaskScene = scene_manager.create_scene(
                self.scene.user_id, TaskScene, 
                self.scene.__bot__
            )
            edit_scene.set_taskid(selected_task)

            await edit_scene.start()
            return 'exit'

        elif action == 'set_editor':
            # Назначаем себя редактором задачи
            task = self.scene.data['scene'].get('current_task_data')
            if not task: return

            card_id = task.get('card_id')
            if not card_id:
                return

            user_id = str(self.user.user_id) if self.user else None
            if not user_id:
                user = await User.by_telegram(self.scene.user_id)
                if not user:
                    await callback.answer("Ошибка при получении данных пользователя.", show_alert=True)
                    return
                user_id = str(user.user_id)

            res = await card_events.on_editor(new_editor_id=_UUID(str(user_id)), card_id=_UUID(str(card_id)))

            await callback.answer("Вы назначены редактором задачи.", show_alert=True)
            await self.load_task_details()
            await self.scene.update_page('task-detail')

        elif action == 'delete':
            # Переход на страницу подтверждения удаления
            await self.scene.update_page('delete-confirm')
            return
        
        elif action == 'return_to_work':
            task = self.scene.data['scene'].get('current_task_data')
            if not task: return

            card_id = task.get('card_id')

            # Возвращаем в статус edited (В работе)
            res = await card_service.change_card_status(card_id=card_id, status=CardStatus.edited)

            if res is not None:
                await callback.answer("Задача возвращена в работу.", show_alert=True)
                await self.load_task_details()
                await self.scene.update_page('task-detail')
            else:
                await callback.answer("Ошибка при обновлении статуса.", show_alert=True)

        elif action == 'send_now':
            task = self.scene.data['scene'].get('current_task_data')
            if not task: return

            logger.info(f"Пользователь {get_user_display_name(self.user)} инициирует немедленную отправку задачи '{task.get('name')}' (ID: {task.get('card_id')})")

            card_id = task.get('card_id')

            card_obj = await Card.get_by_id(_UUID(str(card_id)))
            if card_obj and card_obj.status == CardStatus.ready:
                await card_obj.schedule_immediate()
                await callback.answer("🚀 Задача отправлена на публикацию!", show_alert=True)

                await self.load_task_details()
                await self.scene.update_page('task-detail')
            else:
                await callback.answer(
                    "Ошибка: задача не найдена или не в статусе 'готово'.", show_alert=True)