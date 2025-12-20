"""
Страница предпросмотра поста для всех клиентов
"""
from aiogram.types import CallbackQuery
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.constants import CLIENTS
from modules.post_sender import prepare_and_send_preview, download_kaiten_files

class PreviewPage(Page):
    
    __page_name__ = 'post-preview'
    
    # Кэш скачанных файлов (для одной сессии страницы)
    _cached_files: dict = {}
    
    async def data_preparate(self):
        """Подготовка данных перед отображением"""
        card = await self.scene.get_card_data()
        
        if not card:
            await self.scene.update_key(self.__page_name__, 'clients', [])
            return
        
        clients = card.get('clients', [])
        await self.scene.update_key(self.__page_name__, 'clients', clients)
        
        # Предварительно скачиваем файлы если есть
        post_images = card.get('post_images') or []
        task_id = card.get('task_id')
        
        if post_images and task_id:
            cache_key = f"{task_id}:{','.join(post_images)}"
            if cache_key not in self._cached_files:
                downloaded = await download_kaiten_files(task_id, post_images)
                self._cached_files[cache_key] = downloaded
    
    async def content_worker(self) -> str:
        """Возвращает текст сообщения"""
        card = await self.scene.get_card_data()
        clients = self.scene.get_key(self.__page_name__, 'clients') or []
        content_dict = card.get('content') if card else None
        
        if not clients:
            return (
                "👁 Предпросмотр поста\n\n"
                "❌ Каналы не выбраны\n\n"
                "Для предпросмотра поста сначала необходимо выбрать каналы для публикации.\n"
                "Вернитесь назад и настройте каналы публикации."
            )
        
        # Проверяем наличие контента (общего или специфичного)
        has_content = False
        if isinstance(content_dict, dict):
            has_content = bool(content_dict.get('all') or any(content_dict.get(c) for c in clients))
        elif isinstance(content_dict, str):
            has_content = bool(content_dict)
        
        if not has_content:
            return (
                "👁 Предпросмотр поста\n\n"
                "❌ Контент не создан\n\n"
                "Для предпросмотра поста сначала необходимо создать контент.\n"
                "Вернитесь назад и добавьте текст поста."
            )
        
        return self.append_variables()
    
    async def buttons_worker(self) -> list[dict]:
        """Создает кнопки с клиентами"""
        buttons = []
        card = await self.scene.get_card_data()
        clients = self.scene.get_key(self.__page_name__, 'clients') or []
        content_dict = card.get('content') if card else None
        
        # Проверяем наличие контента
        has_content = False
        if isinstance(content_dict, dict):
            has_content = bool(content_dict.get('all') or any(content_dict.get(c) for c in clients))
        elif isinstance(content_dict, str):
            has_content = bool(content_dict)
        
        # Если нет клиентов или контента, не создаем кнопки предпросмотра
        if not clients or not has_content:
            return buttons
        
        # Создаем кнопки для каждого клиента
        for client in clients:
            # Получаем имя клиента из clients.json
            client_info = CLIENTS.get(client, {})
            client_name = client_info.get('label', client)
            
            buttons.append({
                'text': f"📱 {client_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'preview_client',
                    str(client)
                )
            })
        
        # Кнопка "Показать всем"
        if clients:
            buttons.append({
                'text': "📤 Показать для всех",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'preview_all'
                ),
                'ignore_row': True
            })
        
        return buttons
    
    @Page.on_callback('preview_client')
    async def preview_client_handler(self, callback: CallbackQuery, args: list):
        """Обработчик предпросмотра для клиента"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан клиент")
            return
        
        client = args[1]
        await self.preview_for_client(callback, client)
    
    @Page.on_callback('preview_all')
    async def preview_all_handler(self, callback: CallbackQuery, args: list):
        """Обработчик отправки всем клиентам"""
        await self.preview_all_clients(callback)
    
    async def preview_for_client(self, callback: CallbackQuery, client: str):
        """Отправляет предпросмотр поста и entities для конкретного клиента"""
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        # Получаем контент для клиента (сначала специфичный, потом общий)
        content_dict = card.get('content', {})
        if isinstance(content_dict, dict):
            content = content_dict.get(client) or content_dict.get('all', '')
        else:
            # Обратная совместимость со старым форматом
            content = content_dict if isinstance(content_dict, str) else ''
        
        tags = card.get('tags', [])
        post_images = card.get('post_images') or []
        task_id = card.get('task_id')
        card_id = card.get('card_id')
        
        try:
            result = await prepare_and_send_preview(
                bot=self.scene.__bot__,
                chat_id=callback.message.chat.id,
                content=content,
                tags=tags,
                client_key=client,
                post_images=post_images,
                cached_files=self._cached_files,
                card_id=card_id
            )

            if result['success']:
                await callback.answer("✅ Предпросмотр показан")

            else:
                await callback.answer(f"❌ Ошибка: {result.get('error', 'unknown')[:50]}", 
                                      show_alert=True)
        
        except Exception as e:
            print(f"Error sending preview: {e}")
            await callback.answer("❌ Ошибка при показе предпросмотра")
    
    
    async def preview_all_clients(self, callback: CallbackQuery):
        """Показывает предпросмотр поста для всех клиентов"""
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        clients = card.get('clients', [])
        
        if not clients:
            await callback.answer("❌ Нет каналов для предпросмотра")
            return
        
        await callback.answer("📤 Показываю предпросмотры...")
        
        for client in clients:
            await self.preview_for_client(callback, client)

