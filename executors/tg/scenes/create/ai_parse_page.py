import json
import asyncio
from datetime import datetime
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import brain_api
from modules.constants import SETTINGS


class AIParserPage(Page):
    """Страница для преобразования текста в структурированные данные с помощью AI"""
    
    __page_name__ = 'ai-parse'
    
    def __post_init__(self):
        """Инициализация состояния страницы"""
        self.max_retries = 3
    
    async def content_worker(self) -> str:
        self.clear_content()
        
        page_data = self.get_data()
        parsed_data = page_data.get('parsed_data') if page_data else None
        parse_error = page_data.get('parse_error') if page_data else None
        is_loading = page_data.get('is_loading', False) if page_data else False
        
        if is_loading:
            self.content += '\n\n⏳ *Парсится...*\n\nПожалуйста, подождите — результат будет отправлен автоматически.'
        elif parse_error:
            self.content += f'\n\n❌ **Ошибка парсинга**\n\n{parse_error}'
        elif parsed_data:
            self.content += '\n\n✅ **Данные успешно распознаны:**\n\n'
            self.content += f'📌 **Название:** `{parsed_data.get("name", "➖")}`\n'
            self.content += f'📄 **Описание:** `{parsed_data.get("description", "➖")}`\n'
            self.content += f'🖼 **ТЗ для дизайнеров:** `{parsed_data.get("image", "➖")}`\n'
            self.content += f'⏰ **Дедлайн:** `{parsed_data.get("deadline", "➖")}`\n'
            
            # Отображаем теги
            tags = parsed_data.get('tags', [])
            if tags:
                tag_options = {
                    key: tag['name'] 
                    for key, tag in SETTINGS['properties']['tags']['values'].items()
                }
                tag_names = [tag_options.get(t, t) for t in tags]
                self.content += f'🏷 **Хештеги:** {", ".join(tag_names)}'
            else:
                self.content += '🏷 **Хештеги:** ➖'
        
        return self.content
    
    async def buttons_worker(self) -> list[dict]:
        result = await super().buttons_worker()
        
        page_data = self.get_data()
        parsed_data = page_data.get('parsed_data') if page_data else None
        
        if parsed_data:
            result.append({
                'text': '✅ Подтвердить данные',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'confirm_parsed_data'
                )
            })
            result.append({
                'text': '🔄 Ввести заново',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'reset_parsed_data'
                )
            })
        
        return result
    
    @Page.on_text('str')
    async def handle_text_input(self, message, value: str):
        """Отправка введённого текста на парсинг AI (fire-and-forget).

        Результат придёт в `/events/ai_callback` и будет обработан методом `on_ai_parsed_result`.
        """
        # Сбрасываем старые результаты и ставим индикатор загрузки
        await self.update_data('parsed_data', None)
        await self.update_data('parse_error', None)
        await self.update_data('checked_text', value)
        await self.update_data('is_loading', True)
        await self.scene.update_message()

        # Отправляем асинхронный запрос к AI
        asyncio.create_task(self._send_parse_request(value))

    async def _send_parse_request(self, text: str):
        """Отправляет текст на парсинг в brain-api с callback-метаданными."""
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        tag_options = {
            key: tag['name'] 
            for key, tag in SETTINGS['properties']['tags']['values'].items()
        }
        tags_list = ', '.join([f'"{key}" ({name})' for key, name in tag_options.items()])

        prompt = (
            f"Текущая дата и время: {current_datetime}\n\n"
            "Преобразуй следующий текст в JSON с ключами:\n"
            '- "name": строка - общее название задания (краткое, максимум 100 символов)\n'
            '- "description": строка - подробное описание задания для написания поста (нужно сохранить как можно БОЛЬШЕ ИНФОРМАЦИИ, максимум 2096 символов. По возможности красиво оформить. Без маркдаун, но с разделением по строкам и тд.)\n'
            '- "image": строка - техническое задание для дизайнеров (сухая тема поста, максимум 256 символов)\n'
            '- "deadline": строка - дедлайн задания в формате ISO 8601 (например: 2025-12-01T18:00:00)\n'
            f'- "tags": массив строк - теги задания из списка доступных: [{tags_list}]. Верни массив ключей (не названий) подходящих тегов. Название в скобках, нужный ключ в "key"\n\n'
            "Если какой-то из ключей невозможно определить из текста, поставь null (для tags - пустой массив []).\n"
            "Ответь ТОЛЬКО валидным JSON без дополнительного текста, markdown-разметки или пояснений.\n\n"
            f"Текст:\n{text}"
        )

        payload = {
            'prompt': prompt,
            'callback': {
                'user_id': self.scene.user_id,
                'scene': self.scene.__scene_name__,
                'page': self.__page_name__,
                'function': 'on_ai_parsed_result'
            }
        }

        try:
            resp, status = await brain_api.post('/ai/send', data=payload)
            if status != 200:
                logger.error(f"Failed to send AI parse request for user {self.scene.user_id}: status={status} resp={resp}")
                await self.update_data('parse_error', '❌ **Ошибка при отправке запроса в AI. Попробуйте позже.**')
                await self.update_data('is_loading', False)
                await self.scene.update_message()
        except Exception as e:
            logger.error(f"Exception while sending AI parse request for user {self.scene.user_id}: {e}")
            await self.update_data('parse_error', '❌ **Ошибка при отправке запроса в AI. Попробуйте позже.**')
            await self.update_data('is_loading', False)
            await self.scene.update_message()

    async def on_ai_parsed_result(self, result: str):
        """Обработка результата парсинга от AI: пытаемся распарсить JSON и сохранить parsed_data/parse_error."""
        try:
            ai_response = result if isinstance(result, str) else str(result)
            ai_response = ai_response.strip()
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.startswith('```'):
                ai_response = ai_response[3:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            ai_response = ai_response.strip()

            parsed = json.loads(ai_response)
            if not isinstance(parsed, dict):
                raise ValueError('AI вернул не объект')

            # Приводим к нужному формату и обрезаем по максимальной длине
            name = parsed.get('name')
            description = parsed.get('description')
            image = parsed.get('image')
            raw_tags = parsed.get('tags', [])

            tag_options = {
                key: tag['name'] 
                for key, tag in SETTINGS['properties']['tags']['values'].items()
            }
            valid_tags = [t for t in (raw_tags if isinstance(raw_tags, list) else []) if t in tag_options]

            result_data = {
                'name': name[:100] if name else None,
                'description': description[:2096] if description else None,
                'image': image[:256] if image else None,
                'deadline': parsed.get('deadline'),
                'tags': valid_tags
            }

            await self.update_data('parsed_data', result_data)
            await self.update_data('parse_error', None)
            await self.update_data('is_loading', False)
            if self.scene.current_page.__page_name__ == self.__page_name__:
                await self.scene.update_page(self.__page_name__)

        except json.JSONDecodeError as e:
            await self.update_data('parsed_data', None)
            await self.update_data('parse_error', f"Ошибка парсинга JSON: {e}")
            await self.update_data('is_loading', False)
            if self.scene.current_page.__page_name__ == self.__page_name__:
                await self.scene.update_page(self.__page_name__)
        except Exception as e:
            await self.update_data('parsed_data', None)
            await self.update_data('parse_error', f"Неожиданная ошибка: {e}")
            await self.update_data('is_loading', False)
            if self.scene.current_page.__page_name__ == self.__page_name__:
                await self.scene.update_page(self.__page_name__)

    @Page.on_callback('confirm_parsed_data')
    async def confirm_parsed_data_handler(self, callback, args):
        """Подтверждение распарсенных данных и сохранение в сцену"""
        
        page_data = self.get_data()
        parsed_data = page_data.get('parsed_data') if page_data else None
        
        if not parsed_data:
            return
        
        # Сохраняем данные в сцену
        if parsed_data.get('name'):
            await self.scene.update_key('scene', 'name', parsed_data['name'])
        
        if parsed_data.get('description'):
            await self.scene.update_key('scene', 'description', parsed_data['description'])
        
        if parsed_data.get('image'):
            await self.scene.update_key('scene', 'image', parsed_data['image'])
        
        if parsed_data.get('deadline'):
            await self.scene.update_key('scene', 'publish_date', parsed_data['deadline'])
        
        if parsed_data.get('tags'):
            await self.scene.update_key('scene', 'tags', parsed_data['tags'])
        
        # Очищаем временные данные страницы
        await self.update_data('parsed_data', None)
        await self.update_data('parse_error', None)
        
        # Переходим на главную страницу
        await self.scene.update_page('main')
    
    @Page.on_callback('reset_parsed_data')
    async def reset_parsed_data_handler(self, callback, args):
        """Сброс распарсенных данных для повторного ввода"""
        
        await self.update_data('parsed_data', None)
        await self.update_data('parse_error', None)
        await self.scene.update_message()
