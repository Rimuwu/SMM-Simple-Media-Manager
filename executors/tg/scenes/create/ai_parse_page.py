import json
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
        
        if parse_error:
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
        """Обработка введённого текста и отправка на парсинг AI"""
        
        parsed_data = None
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                parsed_data, error = await self._parse_with_ai(value)
                
                if parsed_data:
                    # Успешно распарсили
                    await self.update_data('parsed_data', parsed_data)
                    await self.update_data('parse_error', None)
                    await self.scene.update_message()
                    return
                
                last_error = error
                
            except Exception as e:
                last_error = str(e)
        
        # Все попытки неуспешны
        await self.update_data('parsed_data', None)
        await self.update_data('parse_error', f'Не удалось распарсить данные после {self.max_retries} попыток.\nПоследняя ошибка: {last_error}')
        await self.scene.update_message()
    
    async def _parse_with_ai(self, text: str) -> tuple[dict | None, str | None]:
        """Отправка текста на парсинг AI и получение структурированных данных"""
        
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
        
        try:
            response, status = await brain_api.post(
                '/ai/send',
                data={'prompt': prompt}
            )
            
            if status != 200:
                return None, f"Ошибка API: статус {status}"
            
            # Пытаемся распарсить JSON из ответа
            ai_response = response if isinstance(response, str) else str(response)
            
            # Убираем возможные markdown-обёртки
            ai_response = ai_response.strip()
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.startswith('```'):
                ai_response = ai_response[3:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            ai_response = ai_response.strip()
            
            parsed = json.loads(ai_response)
            
            # Проверяем наличие нужных ключей
            if not isinstance(parsed, dict):
                return None, "AI вернул не объект"
            
            # Приводим к нужному формату и обрезаем по максимальной длине
            name = parsed.get('name')
            description = parsed.get('description')
            image = parsed.get('image')
            
            # Валидируем теги - оставляем только существующие
            raw_tags = parsed.get('tags', [])
            print(raw_tags)
            valid_tags = [t for t in raw_tags if t in tags_list
                          ] if isinstance(raw_tags, list) else []
            
            result = {
                'name': name[:100] if name else None,
                'description': description[:2096] if description else None,
                'image': image[:256] if image else None,
                'deadline': parsed.get('deadline'),
                'tags': valid_tags
            }
            
            return result, None
            
        except json.JSONDecodeError as e:
            return None, f"Ошибка парсинга JSON: {e}"
        except Exception as e:
            return None, f"Неожиданная ошибка: {e}"
    
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
