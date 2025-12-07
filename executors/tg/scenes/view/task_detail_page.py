from os import getenv
from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import get_cards, brain_api, get_users, get_kaiten_users_dict
from global_modules.classes.enums import CardStatus, UserRole
from tg.scenes.edit.task_scene import TaskScene
from tg.oms.manager import scene_manager
from modules.api_client import get_user_role
from modules.constants import SETTINGS
from tg.utils.viewers import viewers_manager
from modules.logs import executors_logger as logger


class TaskDetailPage(Page):
    __page_name__ = 'task-detail'

    async def data_preparate(self) -> None:
        # Загружаем детальную информацию о задаче
        role = self.scene.data['scene'].get('user_role')
        
        if role is None:
            telegram_id = self.scene.user_id
            user_role = await get_user_role(telegram_id)
            await self.scene.update_key('scene', 'user_role', user_role or None)

        # Регистрируем просмотр
        task_id = self.scene.data['scene'].get('selected_task')
        if task_id:
            user_name = self.scene.data['scene'].get('user_name', f"User {self.scene.user_id}")
            # Пытаемся получить имя пользователя из сцены или API, если его нет
            if 'user_name' not in self.scene.data['scene']:
                 # Можно добавить логику получения имени, если критично
                 pass
            
            # Используем имя из Telegram события, если доступно (обычно доступно в хендлерах, но здесь Page)
            # В данном контексте просто используем ID если нет имени, или можно передать имя при входе в сцену
            # Для простоты пока оставим ID или заглушку, если имя не сохранено
            
            user_name = self.scene.data['scene'].get('user_name', f"User {self.scene.user_id}")
            viewers_manager.update_viewer(str(task_id), self.scene.user_id, user_name)

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
            CardStatus.ready: "✅ Готова",
            CardStatus.sent: "🚀 Отправлено"
        }

        # Получаем пользователей для отображения имен
        all_users = await get_users()
        kaiten_users = await get_kaiten_users_dict()
        
        # Форматируем исполнителя
        executor_id = task.get('executor_id')
        executor_name = 'Не назначен'
        if executor_id:
            user_data = next((u for u in all_users if str(u['user_id']) == str(executor_id)), None)
            if user_data:
                executor_name = await get_display_name(
                    user_data['telegram_id'], 
                    kaiten_users, self.scene.__bot__, 
                    user_data.get('tasker_id')
                )

        # Форматируем заказчика
        customer_id = task.get('customer_id')
        customer_name = 'Не указан'
        if customer_id:
            user_data = next((u for u in all_users if str(u['user_id']) == str(customer_id)), None)
            if user_data:
                customer_name = await get_display_name(
                    user_data['telegram_id'], 
                    kaiten_users, self.scene.__bot__,
                    user_data.get('tasker_id')
                )
        
        # Форматируем дедлайн
        deadline = task.get('deadline')
        if deadline:
            from datetime import datetime
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
            from datetime import datetime
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

        # Ссылка на Kaiten
        kaiten_task_id = task.get('task_id')
        kaiten_domain = getenv('KAITEN_DOMAIN', 'demo.kaiten.ru')

        if 'http' not in kaiten_domain:
             kaiten_domain = f"https://{kaiten_domain}"
        space = SETTINGS['space']['id']

        # demo.kaiten.ru/space/667420/card/58354102
        kaiten_link = f"{kaiten_domain}.kaiten.ru/space/{space}/card/{kaiten_task_id}" if kaiten_task_id else "Недоступно"

        # Подготавливаем переменные для шаблона
        add_vars = {
            'task_name': task.get('name', 'Без названия'),
            'task_description': task.get('description', 'Нет описания'),
            'status': status_names.get(task.get('status'), task.get('status', 'Неизвестно')),
            'executor': executor_name,
            'customer': customer_name,
            'deadline': deadline_str,
            'channels': channels_str,
            'tags': tags_str,
            'image_prompt': task.get('image_prompt') or 'Не указано',
            'kaiten_link': kaiten_link,
            'send_time': send_time_str
        }

        # Сохраняем данные задачи в сцену для использования в других методах
        await self.scene.update_key('scene', 'current_task_data', task)

        # Получаем список просматривающих
        viewers = viewers_manager.get_viewers(str(task_id), exclude_user_id=self.scene.user_id)
        viewers_str = ', '.join(viewers) if viewers else 'Никого'

        add_vars['viewers'] = viewers_str

        self.content = self.append_variables(**add_vars)
        self.content = self.content.replace('None', '➖')

    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()

        # Простые кнопки-заглушки для взаимодействия с задачей
        action_buttons = []

        role = self.scene.data['scene'].get('user_role')
        is_admin = role == UserRole.admin

        if role == UserRole.admin or is_admin:
            action_buttons.extend([
                ('assign_executor', '👷 Исполнитель'),
                ('delete', '🗑️ Удалить задачу')
            ])

        if role == UserRole.copywriter or is_admin or role == UserRole.editor:
            action_buttons.extend([
                ('open_task', '📂 Открыть задачу')
            ])
        
        # Кнопки для статуса Ready (Админы и Редакторы)
        current_task = self.scene.data['scene'].get('current_task_data', {})
        task_status = current_task.get('status')
        
        # Если задача отправлена (sent), то для всех кроме админа кнопок нет (или только выход)
        # Для админа - только удаление
        if task_status == CardStatus.sent:
            if is_admin:
                return [{
                    'text': '🗑️ Удалить задачу',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__, 
                        'task_action',
                        'delete'
                    )
                }]
            else:
                return [] # Пустой список кнопок (только "Назад" от сцены если есть)

        # Кнопка "Вернуть в работу" для исполнителя, если задача завершена (ready)
        is_executor = False
        if role == UserRole.copywriter:
             # Проверяем, является ли текущий пользователь исполнителем этой задачи
             executor_data = current_task.get('executor')
             if executor_data and str(executor_data.get('telegram_id')) == str(self.scene.user_id):
                 is_executor = True

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
                    ('change_name', '✏️ Изменить название'),
                    ('change_description', '📝 Изменить описание'),
                ])
            action_buttons.extend([
                ('change_deadline', '⏰ Изменить дедлайн'),
                ('add_comment', '💬 Добавить комментарий')
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

        elif action == 'delete':
            # Удаляем задачу
            task = self.scene.data['scene'].get('current_task_data')
            if not task:
                return

            card_id = task.get('card_id')
            if not card_id:
                return
            
            logger.info(f"Пользователь {self.scene.user_id} запросил удаление задачи {card_id}")

            res, status = await brain_api.delete(
                f'/card/delete/{card_id}',
            )

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
            res, status = await brain_api.post(
                '/card/update',
                data={
                    'card_id': card_id,
                    'status': CardStatus.edited
                }
            )
            
            if status == 200:
                # Отменяем все запланированные задачи (уведомления и т.д.)
                # Это делается автоматически в brain-api при смене статуса или удалении, 
                # но если нужно явно "убрать все таски", то это может означать удаление напоминаний.
                # В brain-api/routers/card.py нет явного удаления тасков при смене статуса на edited,
                # кроме перепланирования при смене дедлайна.
                # Но пользователь просил "убрать все таски".
                # Добавим вызов cancel_card_tasks через API, если такой эндпоинт есть, или добавим его.
                # В brain-api есть cancel_card_tasks, но он не экспортирован в API явно как отдельный метод,
                # кроме как при удалении карты.
                # Однако, при смене статуса на edited, логично, что задачи публикации (если были) должны быть отменены?
                # Или задачи напоминания?
                # Предположим, что речь о задачах публикации, если задача была ready.
                # В brain-api при смене статуса на ready создаются задачи. При возврате - надо удалять.
                # Добавим логику в brain-api/routers/card.py для удаления задач при смене статуса с ready на другой.
                
                await callback.answer("Задача возвращена в работу.", show_alert=True)
                await self.load_task_details()
                await self.scene.update_page('task-detail')
            else:
                await callback.answer("Ошибка при обновлении статуса.", show_alert=True)

        elif action == 'send_now':
            task = self.scene.data['scene'].get('current_task_data')
            if not task: return

            card_id = task.get('card_id')
            
            # Вызываем специальный эндпоинт для немедленной отправки
            res, status = await brain_api.post(
                '/card/send-now',
                data={
                    'card_id': card_id
                }
            )
            
            if status == 200:
                await callback.answer("🚀 Задача отправлена на публикацию!", show_alert=True)
                await self.load_task_details()
                await self.scene.update_page('task-detail')
            else:
                error_detail = res.get('detail', 'Неизвестная ошибка') if isinstance(res, dict) else str(res)
                await callback.answer(f"Ошибка: {error_detail}", show_alert=True)