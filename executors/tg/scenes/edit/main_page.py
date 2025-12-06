from datetime import datetime
from tg.oms import Page
from modules.api_client import get_cards, get_user_role
from modules.constants import SETTINGS
from global_modules.classes.enums import CardStatus
from modules.logs import executors_logger as logger

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
                channels_text = ', '.join(
                    SETTINGS['properties']['channels']['values'].get(ch, {}).get('name', ch)
                    for ch in channels
                ) if channels else 'Не указаны'
                
                # Форматируем теги - преобразуем ключи в имена из настроек
                tags = card.get('tags', [])
                tags_text = ', '.join(
                    SETTINGS['properties']['tags']['values'].get(tag, {}).get('name', tag)
                    for tag in tags
                ) if tags else 'Не указаны'
                
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
                status_names = {
                    CardStatus.pass_.value: "⏳ Создано",
                    CardStatus.edited.value: "✏️ В работе",
                    CardStatus.review.value: "🔍 На проверке", 
                    CardStatus.ready.value: "✅ Готова",
                    CardStatus.sent.value: "🚀 Отправлено"
                }
                status = status_names.get(card.get('status'), card.get('status', 'Неизвестно'))
                
                # Если статус "Отправлено", закрываем сцену
                if card.get('status') == CardStatus.sent.value:
                    logger.info(f"Сцена редактирования задачи {task_id} закрыта для пользователя {self.scene.user_id} (статус 'Отправлено')")
                    await self.scene.bot.send_message(
                        chat_id=self.scene.user_id,
                        text="🚀 Задача была отправлена и закрыта для редактирования."
                    )
                    await self.scene.end()
                    return
                
                # Форматируем контент для отображения
                content = card.get('content', 'Не указан')
                if content and content != 'Не указан':
                    content_display = content[:200] + '...' if len(content) > 200 else content
                    content_block = f'Текущий контент:\n```\n{content_display}\n```'
                else:
                    content_block = 'Контент пока не указан'
                
                # Проверяем наличие комментариев
                editor_notes = card.get('editor_notes', [])
                has_notes = len(editor_notes) > 0
                
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
                    'tags_list': tags,
                    'has_notes': has_notes,
                    'notes_count': len(editor_notes)
                })
                await self.scene.save_to_db()
    
    async def to_page_preworker(self, to_page_buttons: dict) -> dict:
        """Фильтруем кнопки в зависимости от роли и статуса"""
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            cards = await get_cards(card_id=task_id)
            if cards:
                card = cards[0]
                status = card.get('status')
                
                # Проверяем роль пользователя
                user_role = await get_user_role(self.scene.user_id)

                # Если статус "На проверке" или "Готов" и роль "копирайтер" - оставляем только комментарии и превью
                if status in [CardStatus.review.value, CardStatus.ready.value] and user_role == 'copywriter':
                    allowed_pages = ['editor-notes', 'post-preview']
                    return {k: v for k, v in to_page_buttons.items() if k in allowed_pages}

                if status == CardStatus.sent.value and user_role == 'copywriter':
                    return {}

        return to_page_buttons
    
    async def buttons_worker(self):
        """Добавляем кнопку выхода из сцены"""
        buttons = await super().buttons_worker()
        
        from tg.oms.utils import callback_generator
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
