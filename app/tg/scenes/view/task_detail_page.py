from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.brain_client import brain_client
from global_modules.classes.enums import CardStatus, UserRole
from tg.scenes.edit.task_scene import TaskScene
from tg.oms.manager import scene_manager
from modules.constants import SETTINGS
from modules.logs import logger
from datetime import datetime
from tg.scenes.constants import CARD_STATUS_NAMES


class TaskDetailPage(Page):
    __page_name__ = 'task-detail'

    async def data_preparate(self) -> None:
        # Загружаем детальную информацию о задаче
        role = self.scene.data['scene'].get('user_role')
        self.user = {}

        if role is None:
            telegram_id = self.scene.user_id
            user = await brain_client.get_user(telegram_id=telegram_id)

            if user:
                user_role = user.get('role')
                self.user = user

            await self.scene.update_key('scene', 
                                        'user_role', 
                                        user_role or None)

        if not self.user:
            telegram_id = self.scene.user_id
            user = await brain_client.get_user(telegram_id=telegram_id)
            if user:
                self.user = user

        await self.load_task_details()

    async def load_task_details(self):
        """Загружает краткую информацию о выбранной задаче"""
        self.clear_content()

        task_id = self.scene.data['scene'].get('selected_task')
        if not task_id:
            return

        # Получаем информацию о задаче
        tasks = await brain_client.get_cards(card_id=task_id)
        if not tasks:
            return
        
        task = tasks[0]

        # Форматируем исполнителя
        executor_id = task.get('executor_id')
        executor_name = 'Не назначен'
        if executor_id:
            user_data = await brain_client.get_user(user_id=executor_id)
            if user_data:
                executor_name = await get_display_name(
                    user_data['telegram_id'],
                    self.scene.__bot__
                )

        # Форматируем заказчика
        customer_id = task.get('customer_id')
        customer_name = 'Не указан'
        if customer_id:
            user_data = await brain_client.get_user(user_id=customer_id)
            if user_data:
                customer_name = await get_display_name(
                    user_data['telegram_id'],
                    self.scene.__bot__
                )
        # Форматируем редактора
        editor_id = task.get('editor_id')
        editor_name = 'Не указан'
        if editor_id:
            user_data = await brain_client.get_user(user_id=editor_id)
            if user_data:
                editor_name = await get_display_name(
                    user_data['telegram_id'],
                    self.scene.__bot__
                )

        # Форматируем дедлайн
        deadline = task.get('deadline')
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
                deadline_str = deadline_dt.strftime('%d.%m.%Y %H:%M')
            except:
                deadline_str = deadline
        else:
            deadline_str = 'Не установлен'

        # Форматируем даты отправки
        send_time = task.get('send_time')
        if send_time:
            try:
                send_time_dt = datetime.fromisoformat(send_time)
                send_time_str = send_time_dt.strftime('%d.%m.%Y %H:%M')
            except:
                send_time_str = send_time
        else:
            send_time_str = 'Не установлено'
        
        # Форматируем каналы
        channels = task.get('clients', [])
        if channels:
            channel_names = []
            for ch_key in channels:
                ch_info = SETTINGS['properties']['channels']['values'].get(ch_key)
                if ch_info:
                    channel_names.append(ch_info['name'])
                else:
                    channel_names.append(ch_key)
            channels_str = ', '.join(channel_names)
        else:
            channels_str = 'Не указаны'

        # Форматируем теги
        tags = task.get('tags', [])
        if tags:
            tag_names = []
            for tag_key in tags:
                tag_info = SETTINGS['properties']['tags']['values'].get(tag_key)
                if tag_info:
                    tag_names.append(tag_info['name'])
                else:
                    tag_names.append(tag_key)
            tags_str = ', '.join(tag_names)
        else:
            tags_str = 'Не указаны'

        add_vars = {
            'task_name': task.get(
                'name', 'Без названия'),
            'task_description': task.get(
                'description', 'Нет описания'),
            'status': CARD_STATUS_NAMES.get(
                task.get('status'), 
                task.get('status', 'Неизвестно')
                ),
            'executor': executor_name,
            'customer': customer_name,
            'editor': editor_name,
            'deadline': deadline_str,
            'channels': channels_str,
            'tags': tags_str,
            'send_time': send_time_str
        }

        await self.scene.update_key('scene', 'current_task_data', task)

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
        user_id = self.user.get('user_id', 0)

        is_editor = current_task.get('editor_id', 0) == user_id
        is_executor = current_task.get('executor_id', 0) == user_id
        is_admin = role == UserRole.admin

        if is_admin:
            action_buttons.extend([
                ('assign_executor', '👷 Исполнитель'),
                ('delete', '🗑️ Удалить задачу')
            ])

        if is_executor or is_admin or is_editor:
            action_buttons.extend([
                ('open_task', '📂 Открыть задачу')
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
                ('add_comment', '💬 Добавить комментарий'),
                ('files-view', '📁 Файлы'),
                ('change_description', '📝 Изменить описание')
            ])

            if task_status in [CardStatus.review, CardStatus.ready]:
                action_buttons.extend([
                    ('preview', '👁 Просмотреть пост')
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

        elif action == 'add_comment':
            # Переход на страницу добавления комментария
            await self.scene.update_key('scene', 'comment_text', '')
            await self.scene.update_page('add-comment')
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

            user_id = self.user.get('user_id', 0)
            if not user_id:
                user = await brain_client.get_user(telegram_id=self.scene.user_id)
                if not user:
                    await callback.answer("Ошибка при получении данных пользователя.", show_alert=True)
                    return

                user_id = user.get('user_id', 0)

            res = await brain_client.update_card(
                card_id=card_id,
                editor_id=user_id
            )

            if res is not None:
                await callback.answer("Вы назначены редактором задачи.", show_alert=True)
                await self.load_task_details()
                await self.scene.update_page('task-detail')
            else:
                await callback.answer("Ошибка при назначении редактора.", show_alert=True)

        elif action == 'delete':
            # Удаляем задачу
            task = self.scene.data['scene'].get('current_task_data')
            if not task:
                return

            card_id = task.get('card_id')
            if not card_id:
                return
            
            logger.info(f"Пользователь {self.scene.user_id} запросил удаление задачи {card_id}")

            result = await brain_client.delete_card(card_id)
            status = result.get('status', 200) if isinstance(result, dict) else 200

            if status == 200:
                logger.info(f"Задача {card_id} успешно удалена пользователем {self.scene.user_id}")
                await self.scene.update_key(
                    'scene', 'selected_task', None)
                await self.scene.update_page('task-list')

                await callback.answer("Задача успешно удалена.", show_alert=True)

            else:
                logger.error(f"Ошибка при удалении задачи {card_id} пользователем {self.scene.user_id}: {res}")
                await callback.answer("Ошибка при удалении задачи.", show_alert=True)
        
        elif action == 'return_to_work':
            task = self.scene.data['scene'].get('current_task_data')
            if not task: return

            card_id = task.get('card_id')

            # Возвращаем в статус edited (В работе)
            res = await brain_client.change_card_status(
                card_id=card_id,
                status=CardStatus.edited
            )

            if res is not None:

                await callback.answer("Задача возвращена в работу.", show_alert=True)
                await self.load_task_details()
                await self.scene.update_page('task-detail')
            else:
                await callback.answer("Ошибка при обновлении статуса.", show_alert=True)

        elif action == 'send_now':
            task = self.scene.data['scene'].get('current_task_data')
            if not task: return

            card_id = task.get('card_id')
            
            result = await brain_client.send_now(card_id)
            status = result.get('status', 200) if isinstance(result, dict) else 500
            
            if status == 200:
                await callback.answer("🚀 Задача отправлена на публикацию!", show_alert=True)
                await self.load_task_details()
                await self.scene.update_page('task-detail')

            else:
                error_detail = result.get('detail', 'Неизвестная ошибка') if isinstance(result, dict) else str(result)
                await callback.answer(f"Ошибка: {error_detail}", show_alert=True)