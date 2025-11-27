from tg.oms.utils import callback_generator
from tg.oms import Page
from modules.api_client import brain_api
from modules.constants import SETTINGS

class FinishPage(Page):

    __page_name__ = 'finish'


    def min_values(self):
        data = self.scene.data['scene']
        keys = ['name', 'description', 'publish_date']

        for key in keys:
            if data.get(key, None) in [None, '']:
                return False
        return True

    async def buttons_worker(self) -> list[dict]:
        buttons = []

        if self.min_values():
            buttons.append({
                'text': '❤ Создать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'end'),
                'ignore_row': True
            })

        return buttons
    
    async def content_worker(self) -> str:
        self.clear_content()
        
        # Добавляем количество файлов для отображения
        files = self.scene.data['scene'].get('files', [])
        add_vars = {
            'files_count': len(files)
        }
        
        content = self.append_variables(**add_vars)

        if not self.min_values():
            content += '\n\n❗️ Не все обязательные поля заполнены. Пожалуйста, вернитесь и заполните их.'

        return content

    @Page.on_callback('end')
    async def on_end(self, callback, args):
        await callback.answer('Создание карточки...')
        data = self.scene.data['scene']

        customer_id, status = await brain_api.get(
            '/user/get',
            params={'telegram_id': self.scene.user_id}
        )

        if status and status == 200:
            if isinstance(customer_id, list) and len(customer_id) > 0:
                customer_id = customer_id[0]['user_id']
            else:
                customer_id = None

        else:
            customer_id = None

        executor_id = None
        if self.scene.data['scene'].get('user', None):
            executor_id, status = await brain_api.get(
                '/user/get',
                params={'tasker_id': self.scene.data['scene'].get(
                    'user', None)}
            )

            if status and status == 200:
                if isinstance(executor_id, list) and len(executor_id) > 0:
                    executor_id = executor_id[0]['user_id']
                else:
                    executor_id = None

            else:
                executor_id = None

        res, status = await brain_api.post(
            '/card/create',
            data={
                'title': data['name'],
                'description': data['description'],
                'deadline': data['publish_date'],
                'channels': data['channels'],
                'editor_check': True,
                'image_prompt': data['image'],
                'tags': data['tags'],
                'type_id': data['type'],
                'executor_id': executor_id,
                'customer_id': customer_id
            }
        )

        if status and status == 200:
            if 'card_id' in res:
                card_id = res['card_id']
                
                # Загружаем файлы если они есть
                files = data.get('files', [])
                if files:
                    await self._upload_files_to_card(card_id, files)
                
                await self.scene.end()

                await self.scene.__bot__.send_message(
                    self.scene.user_id,
                    f'✅ Задача успешно создана c ID: {card_id}\n'
                    f'📎 Загружено файлов: {len(files)}'
                )
            else:
                await self.scene.__bot__.send_message(
                    self.scene.user_id,
                    f'❌ Произошла ошибка при создании задачи: {res.get("error", "Неизвестная ошибка")}'
                )
        else:
            await self.scene.__bot__.send_message(
                self.scene.user_id,
                f'❌ Произошла ошибка при создании задачи: {res.get("error", "Неизвестная ошибка") if res else "Ошибка сервера"}'
            )
    
    async def _upload_files_to_card(self, card_id: str, files: list):
        """Загрузка файлов в карточку Kaiten"""
        import aiohttp
        
        uploaded_count = 0
        
        for file_info in files:
            try:
                # Получаем файл от Telegram
                file_id = file_info.get('file_id')
                file_name = file_info.get('name', 'file')
                
                # Скачиваем файл
                tg_file = await self.scene.__bot__.get_file(file_id)
                
                if not tg_file or not tg_file.file_path:
                    print(f"Не удалось получить путь к файлу {file_name}")
                    continue
                
                # Скачиваем содержимое файла
                file_bytes = await self.scene.__bot__.download_file(tg_file.file_path)
                
                if not file_bytes:
                    print(f"Не удалось скачать файл {file_name}")
                    continue
                
                file_content = file_bytes.read()
                
                # Формируем multipart/form-data и отправляем напрямую через aiohttp
                form_data = aiohttp.FormData()
                form_data.add_field('card_id', str(card_id))
                form_data.add_field('file', file_content, filename=file_name)
                
                # Загружаем файл в Kaiten через API
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f'{brain_api.base_url}/kaiten/upload-file',
                        data=form_data
                    ) as response:
                        if response.status == 200:
                            uploaded_count += 1
                            print(f"Файл {file_name} успешно загружен")
                        else:
                            error_text = await response.text()
                            print(f"Ошибка загрузки файла {file_name}: статус {response.status}, ответ: {error_text}")
                
            except Exception as e:
                # Логируем ошибку но продолжаем загружать остальные файлы
                print(f"Ошибка загрузки файла {file_info.get('name')}: {e}")
        
        return uploaded_count