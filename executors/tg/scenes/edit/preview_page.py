"""
Страница предпросмотра поста для всех клиентов
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, BufferedInputFile
from aiogram import Bot
from tg.oms import Page
from modules.api_client import brain_api
from global_modules.brain_client import brain_client
from modules.post_generator import generate_post
from modules.constants import SETTINGS, CLIENTS


class PreviewPage(Page):
    
    __page_name__ = 'post-preview'
    
    # Кэш скачанных изображений (для одной сессии страницы)
    _cached_images: dict = {}
    
    async def data_preparate(self):
        """Подготовка данных перед отображением"""
        card = await self.scene.get_card_data()
        
        if not card:
            await self.scene.update_key(self.__page_name__, 'clients', [])
            return
        
        clients = card.get('clients', [])
        await self.scene.update_key(self.__page_name__, 'clients', clients)
        
        # Предварительно скачиваем изображения если есть
        post_images = card.get('post_images') or []
        task_id = card.get('task_id')
        cache_key = f"{task_id}:{','.join(post_images)}"
        
        if post_images and task_id and cache_key not in self._cached_images:
            downloaded = await self.download_kaiten_images(task_id, post_images)
            self._cached_images[cache_key] = downloaded
    
    async def content_worker(self) -> str:
        """Возвращает текст сообщения"""
        card = await self.scene.get_card_data()
        clients = self.scene.get_key(self.__page_name__, 'clients') or []
        content = card.get('content') if card else None
        
        if not clients:
            return (
                "👁 Предпросмотр поста\n\n"
                "❌ Каналы не выбраны\n\n"
                "Для предпросмотра поста сначала необходимо выбрать каналы для публикации.\n"
                "Вернитесь назад и настройте каналы публикации."
            )
        
        if not content:
            return (
                "👁 Предпросмотр поста\n\n"
                "❌ Контент не создан\n\n"
                "Для предпросмотра поста сначала необходимо создать контент.\n"
                "Вернитесь назад и добавьте текст поста."
            )
        
        return self.append_variables()
    
    async def buttons_worker(self) -> list[dict]:
        """Создает кнопки с клиентами"""
        from tg.oms.utils import callback_generator
        
        buttons = []
        card = await self.scene.get_card_data()
        clients = self.scene.get_key(self.__page_name__, 'clients') or []
        content = card.get('content') if card else None
        
        # Если нет клиентов или контента, не создаем кнопки предпросмотра
        if not clients or not content:
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
                )
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
    
    async def download_kaiten_images(self, task_id: int, file_names: list[str]) -> list[bytes]:
        """Скачать изображения из Kaiten по именам файлов"""
        if not task_id or not file_names:
            return []
        
        downloaded = []
        
        try:
            # Получаем список файлов из Kaiten
            response = await brain_client.get_kaiten_files(task_id)
            if not response or not response.get('files'):
                return []
            
            kaiten_files = response['files']
            
            for file_name in file_names:
                # Ищем файл по имени
                target = next((f for f in kaiten_files if f.get('name') == file_name), None)
                if not target:
                    continue
                
                file_id = target.get('id')
                if not file_id:
                    continue
                
                # Скачиваем файл
                file_data, status = await brain_api.get(
                    f"/kaiten/files/{file_id}",
                    params={"task_id": task_id},
                    return_bytes=True
                )
                
                if status == 200 and isinstance(file_data, bytes):
                    downloaded.append(file_data)
        
        except Exception as e:
            print(f"Error downloading kaiten images: {e}")
        
        return downloaded
    
    async def preview_for_client(self, callback: CallbackQuery, client: str):
        """Отправляет предпросмотр поста для конкретного клиента"""
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        content = card.get('content', '')
        tags = card.get('tags', [])
        post_images = card.get('post_images') or []  # list[str] - имена файлов
        task_id = card.get('task_id')
        
        # Генерируем текст поста с тегом клиента
        post_text = generate_post(content, tags, client_key=client)

        # Создаем клавиатуру с кнопкой удаления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить тестовое сообщение", callback_data="delete_message")]
        ])
        
        try:
            # Используем кэш или скачиваем изображения из Kaiten
            downloaded_images = []
            if post_images and task_id:
                cache_key = f"{task_id}:{','.join(post_images)}"
                if cache_key in self._cached_images:
                    downloaded_images = self._cached_images[cache_key]
                else:
                    downloaded_images = await self.download_kaiten_images(task_id, post_images)
                    self._cached_images[cache_key] = downloaded_images
            
            if downloaded_images:
                if len(downloaded_images) == 1:
                    # Одно фото
                    photo = BufferedInputFile(downloaded_images[0], filename="preview.jpg")
                    await callback.message.answer_photo(
                        photo=photo,
                        caption=post_text,
                        parse_mode="html",
                        reply_markup=keyboard
                    )
                else:
                    # Несколько фото - media group
                    from aiogram.types import InputMediaPhoto
                    
                    media_group = []
                    for idx, img_data in enumerate(downloaded_images):
                        photo_input = BufferedInputFile(img_data, filename=f"preview_{idx}.jpg")
                        caption = post_text if idx == 0 else None
                        parse_mode = "html" if idx == 0 else None
                        media_group.append(InputMediaPhoto(
                            media=photo_input,
                            caption=caption,
                            parse_mode=parse_mode
                        ))
                    
                    if media_group:
                        ms = await self.scene.__bot__.send_media_group(
                            chat_id=callback.message.chat.id,
                            media=media_group
                        )
                        id_list = [m.message_id for m in ms]

                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🗑 Удалить тестовое сообщение", callback_data=f"delete_message {' '.join(map(str, id_list))}")]
                            ])
                        # Отправляем отдельно кнопку удаления
                        await callback.message.answer(
                            "👆 Предпросмотр поста выше",
                            reply_markup=keyboard
                        )
            else:
                # Если нет изображений, отправляем только текст
                await callback.message.answer(
                    text=post_text,
                    parse_mode="html",
                    reply_markup=keyboard
                )
            
            await callback.answer("✅ Предпросмотр показан")
        
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
