from datetime import datetime
from modules.utils import get_display_name
from tg.oms.utils import callback_generator
from tg.oms import Page
from modules.api_client import brain_api
from modules.constants import SETTINGS
from tg.oms.common_pages import UserSelectorPage

class FinishPage(Page):

    __page_name__ = 'finish'

    # Флаг, указывающий что создание в процессе — используется для скрытия кнопки
    creating: bool = False

    def min_values(self):
        data = self.scene.data['scene']
        keys = ['name', 'description', 'publish_date']

        for key in keys:
            if data.get(key, None) in [None, '']:
                return False
        return True

    async def buttons_worker(self) -> list[dict]:
        buttons = []

        # Скрываем кнопку во время создания
        if self.min_values() and not getattr(self, 'creating', False):
            buttons.append({
                'text': '❤ Создать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'end'),
                'ignore_row': True
            })

        return buttons
    
    async def content_worker(self) -> str:
        # Если сейчас идёт создание — показываем статус и скрываем обычный контент
        if getattr(self, 'creating', False):
            return '🧸 Создание задачи...'

        self.clear_content()
        add_vars = {}
        data = self.scene.data['scene']

        if data['type'] == 'public':
            add_vars['type'] = 'Общее задание'
        else:
            add_vars['type'] = 'Личное задание'

        # Channels
        channels = data.get('channels', [])
        if channels:
            channel_names = []
            for ch_key in channels:
                ch_info = SETTINGS['properties']['channels']['values'].get(ch_key)
                if ch_info:
                    channel_names.append(ch_info['name'])
                else:
                    channel_names.append(ch_key)
            add_vars['channels'] = ', '.join(channel_names)
        else:
            add_vars['channels'] = '⭕'

        tags = data.get('tags')
        if not tags:
            add_vars['tags'] = '⭕'
        else:
            tag_names = []
            for tag_key in tags:
                tag_info = SETTINGS['properties']['tags']['values'].get(tag_key)
                if tag_info:
                    tag_names.append(tag_info['name'])
                else:
                    tag_names.append(tag_key)
            add_vars['tags'] = ', '.join(tag_names)
        
        # Date
        if data.get('publish_date'):
            try:
                dt = datetime.fromisoformat(data['publish_date'])
                add_vars['publish_date'] = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                add_vars['publish_date'] = data['publish_date']
        else:
            add_vars['publish_date'] = '➖'

        # Send date
        if data.get('send_date'):
            try:
                dt = datetime.fromisoformat(data['send_date'])
                add_vars['send_date'] = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                add_vars['send_date'] = data['send_date']
        else:
            add_vars['send_date'] = '➖'

        # Executor
        from global_modules.brain_client import brain_client
        
        user_id = data.get('user')
        if user_id:
            # Получаем информацию о пользователе

            users = await brain_client.get_users(user_id=str(user_id))

            if users:
                user_data = users[0]
                kaiten_users = await brain_client.get_kaiten_users_dict() if user_data.get('tasker_id') else {}
                
                display_name = await get_display_name(
                    user_data['telegram_id'],
                    kaiten_users,
                    self.scene.__bot__,
                    user_data.get('tasker_id')
                )
                add_vars['user'] = display_name
            else:
                add_vars['user'] = f"ID: {user_id}"
        else:
            add_vars['user'] = '➖'
        
        # Files
        files = data.get('files', [])
        if files:
            add_vars['files'] = f'📎 {len(files)} файл(ов)'
        else:
            add_vars['files'] = '⭕'

        if data.get('description'):
            add_vars['description'] = data['description']
        else:
            add_vars['description'] = 'Без описания'

        # Add note about private type if executor is set
        if user_id:
             add_vars['type'] += ' (будет изменено на Личное)'

        self.content = self.append_variables(**add_vars)
        self.content = self.content.replace('None', '➖')

        if not self.min_values():
            self.content += '\n\n❗️ Не все обязательные поля заполнены. Пожалуйста, вернитесь и заполните их.'

        return self.content

    @Page.on_callback('end')
    async def on_end(self, callback, args):
        # Отправляем быстрый ответ и переводим страницу в режим создания
        await callback.answer('Создание карточки...')
        self.creating = True
        # Обновляем сообщение сцены сразу — уберём кнопку и поменяем текст
        await self.scene.update_message()

        data = self.scene.data['scene']

        # Если указан исполнитель, меняем тип на приватный
        if data.get('user'):
            data['type'] = 'private'

        # Получаем customer_id (заказчик - текущий пользователь)
        from global_modules.brain_client import brain_client
        
        customers = await brain_client.get_users(telegram_id=self.scene.user_id)
        customer_id = customers[0]['user_id'] if customers else None

        # Получаем executor_id
        executor_id = None
        user_value = self.scene.data['scene'].get('user')
        if user_value:
            # user может быть либо user_id (UUID), либо tasker_id (int)
            # Сначала пробуем как user_id
            try:
                executors = await brain_client.get_users(user_id=str(user_value))
                if executors:
                    executor_id = executors[0]['user_id']
                    print(f"Найден исполнитель по user_id {user_value}: {executor_id}")
            except Exception as e:
                print(f"Ошибка получения исполнителя по user_id: {e}")
            
            # Если не нашли, пробуем как tasker_id (только если это число)
            if not executor_id:
                try:
                    # Проверяем, является ли значение числом
                    tasker_id = int(user_value)
                    executors = await brain_client.get_users(tasker_id=tasker_id)
                    if executors:
                        executor_id = executors[0]['user_id']
                        print(f"Найден исполнитель по tasker_id {tasker_id}: {executor_id}")
                except (ValueError, TypeError):
                    print(f"Значение {user_value} не является числом, пропускаем поиск по tasker_id")
                except Exception as e:
                    print(f"Ошибка получения исполнителя по tasker_id: {e}")

        try:
            res, status = await brain_api.post(
                '/card/create',
                data={
                    'title': data['name'],
                    'description': data['description'],
                    'deadline': data['publish_date'],
                    'send_time': data['send_date'],
                    'channels': data['channels'],
                    'need_check': data.get('editor_check', True),
                    'image_prompt': data['image'],
                    'tags': data['tags'],
                    'type_id': data['type'],
                    'executor_id': executor_id,
                    'customer_id': customer_id
                }
            )

            if status and status == 200 and 'card_id' in res:
                card_id = res['card_id']
                files = data.get('files', [])
                uploaded_count = 0

                if files:
                    upload_res = await brain_client.upload_files_to_card(
                        card_id=str(card_id),
                        files=files,
                        bot=self.scene.__bot__
                    )
                    if upload_res:
                        uploaded_count += 1
                    else:
                        print(f"Ошибка загрузки файлов к карточке {card_id}: {upload_res}")

                await self.scene.end()

                await self.scene.__bot__.send_message(
                    self.scene.user_id,
                    f'Задача: "{data["name"]}" успешно создана c ID: {card_id}\n'
                    f'📎 Загружено файлов: {uploaded_count}'
                )
                return

            # Если мы здесь — произошла ошибка
            self.creating = False
            self.clear_content()
            await self.scene.update_message()

            # Сообщаем пользователю об ошибке
            err_text = res.get('error') if isinstance(res, dict) else None
            await self.scene.__bot__.send_message(
                self.scene.user_id,
                f'❌ Произошла ошибка при создании задачи: {err_text or "Неизвестная ошибка"}'
            )

        except Exception as e:
            # В случае исключения откатываем интерфейс
            print(f"Ошибка создания карточки: {e}")
            self.creating = False
            self.clear_content()
            await self.scene.update_message()
            await self.scene.__bot__.send_message(
                self.scene.user_id,
                f'❌ Произошла ошибка при создании задачи: {str(e)[:1024]}'
            )