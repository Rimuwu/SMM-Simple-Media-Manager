from datetime import datetime
from tg.oms import Page
from tg.oms.utils import callback_generator
from app.models.card.Card import Card
from models.User import User
from uuid import UUID as _UUID
from modules.enums import CardStatus
from modules.logs import logger
from tg.scenes.constants import CARD_STATUS_NAMES, format_channels, format_tags

class MainPage(Page):
    
    __page_name__ = 'main-page'
    _card_status_cache: str | None = None
    _card_role_cache: str | None = None
    
    async def data_preparate(self):
        """Загружаем данные задачи"""
        task_id = self.scene.data['scene'].get('task_id')

        if task_id:
            cards = [c.to_full_dict() for c in await Card.find(card_id=task_id)]
            if cards:
                card = cards[0]

                # Форматируем каналы и теги
                channels = card.get('clients', [])
                channels_text = format_channels(channels)
                
                tags = card.get('tags', [])
                tags_text = await format_tags(tags)
                
                # Форматируем даты
                publish_date = card.get('send_time')
                if publish_date:
                    try:
                        publish_date = datetime.fromisoformat(publish_date).strftime('%d.%m.%Y %H:%M')
                    except:
                        pass

                deadline = card.get('deadline')
                if deadline:
                    try:
                        deadline = datetime.fromisoformat(deadline).strftime('%d.%m.%Y %H:%M')
                    except:
                        pass
                
                # Форматируем статус
                status = CARD_STATUS_NAMES.get(card.get('status'), card.get('status', 'Неизвестно'))

                # Форматируем контент для отображения
                content = card.get('content', 'Не указан')
                if content and content != 'Не указан':
                    content_display = content[:200] + '...' if len(content) > 200 else content
                    content_block = f'Текущий контент:\n```\n{content_display}\n```'
                else:
                    content_block = 'Контент пока не указан'
                
                # Обновляем все данные сцены одним вызовом
                self.scene.data['scene'].update({
                    'name': card.get('name', 'Без названия'),
                    'description': card.get('description', 'Нет описания'),
                    'channels': channels_text,
                    'publish_date': publish_date or 'Не указана',
                    'deadline': deadline or 'Не указана',
                    'editors_check': '✅' if card.get('need_check', False) else '❌',
                    'status': status,
                    'tags': tags_text,
                    'content': content,
                    'content_block': content_block,
                    'clients_list': channels,
                    'tags_list': tags
                })
                self._card_status_cache = card.get('status')
                await self.scene.save_to_db()
    
    async def to_page_preworker(self, to_page_buttons: dict) -> dict:
        """Фильтруем кнопки в зависимости от роли и статуса"""
        # Используем статус из кеша data_preparate, иначе из scene.data
        status = self._card_status_cache or self.scene.data['scene'].get('status')

        if status:
            user_role = self._card_role_cache
            if user_role is None:
                user_role = await User.role_for(self.scene.user_id)
                self._card_role_cache = user_role

            # Если статус "На проверке" или "Готов" и роль "копирайтер" - оставляем только комментарии и превью
            if status in [CardStatus.review.value, CardStatus.ready.value] and user_role == 'copywriter':
                allowed_pages = ['post-preview']
                return {k: v for k, v in to_page_buttons.items() if k in allowed_pages}

            if status == CardStatus.sent.value and user_role == 'copywriter':
                return {}

        return to_page_buttons
    
    async def buttons_worker(self):
        """Добавляем кнопку выхода из сцены"""
        buttons = await super().buttons_worker()
        
        buttons.append({
            'text': '🚪 Закрыть задачу',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'exit_scene'
            ),
            'ignore_row': True
        })
        
        return buttons
    
    @Page.on_callback('exit_scene')
    async def exit_scene(self, callback, args):
        """Выход из сцены"""
        await self.scene.end()
        await callback.answer('👋 Задача закрыта')

