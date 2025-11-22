from tg.oms import Page
from modules.api_client import get_cards
from modules.constants import SETTINGS
from global_modules.classes.enums import CardStatus

class MainPage(Page):
    
    __page_name__ = 'main-page'
    
    async def data_preparate(self):
        """Загружаем данные задачи"""
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            cards = await get_cards(card_id=task_id)
            if cards:
                card = cards[0]
                
                # Форматируем каналы - преобразуем ключи в имена из настроек
                channels = card.get('clients', [])
                if channels:
                    channel_names = []
                    for channel_key in channels:
                        channel_info = SETTINGS['properties']['channels']['values'].get(channel_key)
                        if channel_info:
                            channel_names.append(channel_info['name'])
                        else:
                            channel_names.append(channel_key)
                    channels_text = ', '.join(channel_names)
                else:
                    channels_text = 'Не указаны'
                
                # Форматируем теги - преобразуем ключи в имена из настроек
                tags = card.get('tags', [])
                if tags:
                    tag_names = []
                    for tag_key in tags:
                        tag_info = SETTINGS['properties']['tags']['values'].get(tag_key)
                        if tag_info:
                            tag_names.append(tag_info['name'])
                        else:
                            tag_names.append(tag_key)
                    tags_text = ', '.join(tag_names)
                else:
                    tags_text = 'Не указаны'
                
                # Форматируем дату
                publish_date = card.get('deadline')
                if publish_date:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(publish_date)
                        publish_date = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        pass
                
                # Форматируем статус
                status_names = {
                    CardStatus.pass_.value: "⏳ Создано",
                    CardStatus.edited.value: "✏️ В работе",
                    CardStatus.review.value: "🔍 На проверке", 
                    CardStatus.ready.value: "✅ Готова"
                }
                status = status_names.get(card.get('status'), card.get('status', 'Неизвестно'))
                
                # Форматируем контент для отображения
                content = card.get('content', 'Не указан')
                if content and content != 'Не указан':
                    # Ограничиваем длину контента для отображения
                    if len(content) > 200:
                        content_display = content[:200] + '...'
                    else:
                        content_display = content
                    content_block = f'Текущий контент:\n```\n{content_display}\n```'
                else:
                    content_block = 'Контент пока не указан'
                
                # Обновляем данные сцены
                await self.scene.update_key('scene', 'name', card.get('name', 'Без названия'))
                await self.scene.update_key('scene', 'description', card.get('description', 'Нет описания'))
                await self.scene.update_key('scene', 'channels', channels_text)
                await self.scene.update_key('scene', 'publish_date', publish_date or 'Не указана')
                await self.scene.update_key('scene', 'deadline', card.get('deadline', ''))
                await self.scene.update_key('scene', 'editors_check', '✅' if card.get('need_check', False) else '❌')
                await self.scene.update_key('scene', 'status', status)
                await self.scene.update_key('scene', 'tags', tags_text)
                await self.scene.update_key('scene', 'content', content)
                await self.scene.update_key('scene', 'content_block', content_block)
                
                # Сохраняем исходные данные (ключи)
                await self.scene.update_key('scene', 'clients_list', channels)
                await self.scene.update_key('scene', 'tags_list', tags)
