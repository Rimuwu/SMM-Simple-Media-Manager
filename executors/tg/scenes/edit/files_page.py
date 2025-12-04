"""
Страница для просмотра и выбора файлов карточки
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram import Bot
from tg.oms import Page
from modules.api_client import get_cards, brain_api, get_kaiten_files


class FilesPage(Page):
    
    __page_name__ = 'files-view'
    
    def __after_init__(self):
        """Инициализация значений по умолчанию"""
        self.max_files = 10  # Максимальное количество загружаемых файлов

    async def data_preparate(self):
        """Подготовка данных перед отображением"""
        card = await self.scene.get_card_data()
        
        if not card:
            await self.scene.update_key(self.__page_name__, 'files', [])
            await self.scene.update_key(self.__page_name__, 'uploaded_files', [])
            return
        
        # Инициализируем список загруженных файлов если его нет
        if not self.scene.get_key(self.__page_name__, 'uploaded_files'):
            await self.scene.update_key(self.__page_name__, 'uploaded_files', [])
        
        task_id = card.get('task_id')
        
        try:
            # Запрос файлов карточки
            response = await get_kaiten_files(task_id)
            status = 200 if response else 404
            
            if status == 200 and response.get('files'):
                await self.scene.update_key(self.__page_name__, 'files', response['files'])
            else:
                await self.scene.update_key(self.__page_name__, 'files', [])
        except Exception as e:
            print(f"Error getting files: {e}")
            await self.scene.update_key(self.__page_name__, 'files', [])
    
    async def content_worker(self) -> str:
        """Возвращает текст сообщения"""
        uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
        
        add_vars = {
            'uploaded_count': len(uploaded_files),
            'max_files': self.max_files
        }
        
        # Формируем список загруженных файлов для отображения
        if uploaded_files:
            files_list = []
            for idx, file_info in enumerate(uploaded_files, 1):
                file_type = file_info.get('type', 'файл')
                file_name = file_info.get('name', 'без имени')
                files_list.append(f"{idx}. {file_type}: `{file_name}`")
            add_vars['uploaded_files_list'] = '\n'.join(files_list)
        else:
            add_vars['uploaded_files_list'] = ''
        
        return self.append_variables(**add_vars)
    
    async def buttons_worker(self) -> list[dict]:
        """Создает кнопки с файлами"""
        from tg.oms.utils import callback_generator
        
        buttons = []
        files = self.scene.get_key(self.__page_name__, 'files') or []
        uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
        
        # Кнопки для файлов из Kaiten
        for file in files:
            file_id = file.get('id')
            file_name = file.get('name', 'Без названия')
            
            # Ограничиваем длину имени для кнопки
            if len(file_name) > 30:
                file_name = file_name[:27] + "..."
            
            buttons.append({
                'text': f"📎 {file_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'select_file',
                    str(file_id)
                )
            })
        
        # Кнопки для просмотра загруженных файлов
        if uploaded_files:
            for idx, file_info in enumerate(uploaded_files):
                buttons.append({
                    'text': f'👁 Просмотр {idx + 1}',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'view_uploaded',
                        str(idx)
                    )
                })
            
            # Кнопка очистки загруженных файлов
            buttons.append({
                'text': '🗑 Очистить загруженные',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'clear_uploaded'
                ),
                'ignore_row': True
            })
        
        return buttons
    
    @Page.on_callback('select_file')
    async def select_file_handler(self, callback: CallbackQuery, args: list):
        """Обработчик выбора файла - показывает превью"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID файла")
            return
        
        file_id = args[1]
        await self.show_file_preview(callback, file_id)
    
    async def show_file_preview(self, callback: CallbackQuery, file_id: str):
        """Показывает превью файла с кнопками"""
        from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
        from tg.oms.utils import callback_generator
        
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        task_id = card.get('task_id')
        
        try:
            # Получаем бинарные данные файла
            file_data, status = await brain_api.get(
                f"/kaiten/files/{file_id}",
                params={"task_id": task_id},
                return_bytes=True
            )
            
            if status == 200 and isinstance(file_data, bytes):
                # Сохраняем file_id во временные данные страницы
                await self.scene.update_key(self.__page_name__, 'preview_file_id', file_id)
                await self.scene.update_key(self.__page_name__, 'preview_file_data', file_data.hex())
                
                # Создаем кнопки
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Установить",
                            callback_data=callback_generator(
                                self.scene.__scene_name__,
                                'confirm_file',
                                file_id
                            )
                        ),
                        InlineKeyboardButton(
                            text="🗑 Удалить сообщение",
                            callback_data="delete_message"
                        )
                    ]
                ])
                
                # Отправляем фото
                photo = BufferedInputFile(file_data, filename="preview.jpg")
                await callback.message.answer_photo(
                    photo=photo,
                    caption="📷 Предпросмотр изображения\n\nУстановить это изображение для поста?",
                    reply_markup=keyboard
                )
                await callback.answer()
            else:
                await callback.answer("❌ Ошибка при загрузке файла")
        
        except Exception as e:
            print(f"Error showing preview: {e}")
            await callback.answer("❌ Произошла ошибка")
    
    @Page.on_callback('confirm_file')
    async def confirm_file_handler(self, callback: CallbackQuery, args: list):
        """Обработчик подтверждения установки файла"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID файла")
            return
        
        file_id = args[1]
        await self.confirm_file(callback, file_id)
    
    async def confirm_file(self, callback: CallbackQuery, file_id: str):
        """Устанавливает файл в карточку после подтверждения"""
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        card_id = card.get('card_id')
        
        # Получаем сохраненные данные файла
        file_data_hex = self.scene.get_key(self.__page_name__, 'preview_file_data')
        
        if not file_data_hex:
            await callback.answer("❌ Данные файла не найдены")
            return
        
        try:
            # Отправляем hex данные в API для обновления карточки
            from modules.api_client import update_card
            success = await update_card(
                card_id=card_id,
                binary_data=bytes.fromhex(file_data_hex)
            )
            
            if success:
                await callback.answer("✅ Изображение установлено!")
                # Удаляем сообщение с превью
                try:
                    await callback.message.delete()
                except:
                    pass
                # Обновляем основное сообщение сцены
                await self.scene.update_message()
            else:
                await callback.answer("❌ Ошибка при обновлении карточки")
        
        except Exception as e:
            print(f"Error confirming file: {e}")
            await callback.answer("❌ Произошла ошибка")
    
    @Page.on_callback('view_uploaded')
    async def view_uploaded_handler(self, callback: CallbackQuery, args: list):
        """Просмотр загруженного файла"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка: файл не найден')
            return
        
        try:
            from asyncio import sleep
            from tg.oms.utils import list_to_inline, callback_generator
            
            file_idx = int(args[1])
            uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
            
            if file_idx < 0 or file_idx >= len(uploaded_files):
                await callback.answer('❌ Файл не найден')
                return
            
            file_info = uploaded_files[file_idx]
            file_id = file_info.get('file_id')
            file_type = file_info.get('type')
            file_name = file_info.get('name', 'файл')

            delete_mark = list_to_inline([
                {
                    'text': '🧧 Удалить сообщение',
                    'callback_data': 'delete_message',
                    'ignore_row': True
                },
                {
                    'text': '🗑 Удалить файл',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'delete_uploaded',
                        str(file_idx)
                    )
                },
                {
                    'text': '✅ Установить',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'set_uploaded',
                        str(file_idx)
                    )
                }
            ])

            # Отправляем файл пользователю
            if file_type == 'photo':
                await self.scene.__bot__.send_photo(
                    chat_id=self.scene.user_id,
                    photo=file_id,
                    caption=f"📷 Фото: {file_name}",
                    reply_markup=delete_mark
                )
            elif file_type == 'document':
                await self.scene.__bot__.send_document(
                    chat_id=self.scene.user_id,
                    document=file_id,
                    caption=f"📄 Документ: {file_name}",
                    reply_markup=delete_mark
                )
            elif file_type == 'video':
                await self.scene.__bot__.send_video(
                    chat_id=self.scene.user_id,
                    video=file_id,
                    caption=f"🎥 Видео: {file_name}",
                    reply_markup=delete_mark
                )
            
            await callback.answer()

        except Exception as e:
            print(f"Error viewing uploaded file: {e}")
            await callback.answer(f'❌ Ошибка: {str(e)}')
    
    @Page.on_callback('delete_uploaded')
    async def delete_uploaded_handler(self, callback: CallbackQuery, args: list):
        """Удаление загруженного файла"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка: файл не найден')
            return
        
        try:
            file_idx = int(args[1])
            uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
            
            if file_idx < 0 or file_idx >= len(uploaded_files):
                await callback.answer('❌ Файл не найден')
                return
            
            # Удаляем файл из списка
            deleted_file = uploaded_files.pop(file_idx)
            await self.scene.update_key(self.__page_name__, 'uploaded_files', uploaded_files)
            
            await callback.answer(f'✅ Файл "{deleted_file.get("name", "")}" удален')
            await self.scene.update_message()
            try:
                await callback.message.delete()
            except:
                pass
            
        except Exception as e:
            print(f"Error deleting uploaded file: {e}")
            await callback.answer(f'❌ Ошибка: {str(e)}')
    
    @Page.on_callback('clear_uploaded')
    async def clear_uploaded_handler(self, callback: CallbackQuery, args: list):
        """Очистка всех загруженных файлов"""
        await self.scene.update_key(self.__page_name__, 'uploaded_files', [])
        await callback.answer('✅ Все загруженные файлы удалены')
        await self.scene.update_message()
    
    @Page.on_callback('set_uploaded')
    async def set_uploaded_handler(self, callback: CallbackQuery, args: list):
        """Установка загруженного файла как изображение поста"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка: файл не найден')
            return
        
        try:
            file_idx = int(args[1])
            uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
            
            if file_idx < 0 or file_idx >= len(uploaded_files):
                await callback.answer('❌ Файл не найден')
                return
            
            file_info = uploaded_files[file_idx]
            file_id = file_info.get('file_id')
            file_type = file_info.get('type')
            
            # Только фото можно устанавливать
            if file_type != 'photo':
                await callback.answer('❌ Можно устанавливать только фотографии')
                return
            
            # Скачиваем файл
            file = await self.scene.__bot__.get_file(file_id)
            file_bytes = await self.scene.__bot__.download_file(file.file_path)
            
            # Получаем card_id
            card = await self.scene.get_card_data()
            if not card:
                await callback.answer('❌ Карточка не найдена')
                return
            
            card_id = card.get('card_id')
            
            # Обновляем карточку
            from modules.api_client import update_card
            success = await update_card(
                card_id=card_id,
                binary_data=file_bytes.read()
            )
            
            if success:
                await callback.answer('✅ Изображение установлено!')
                try:
                    await callback.message.delete()
                except:
                    pass
                await self.scene.update_message()
            else:
                await callback.answer('❌ Ошибка при обновлении карточки')
        
        except Exception as e:
            print(f"Error setting uploaded file: {e}")
            await callback.answer(f'❌ Ошибка: {str(e)}')
    
    async def photo_handler(self, message: Message) -> None:
        """Обработка фотографий"""
        uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
        
        if len(uploaded_files) >= self.max_files:
            await message.answer(f'❌ Достигнут лимит файлов ({self.max_files})')
            return
        
        # Получаем самую большую версию фото
        photo = message.photo[-1]
        
        file_info = {
            'type': 'photo',
            'file_id': photo.file_id,
            'file_unique_id': photo.file_unique_id,
            'name': f'photo_{len(uploaded_files) + 1}.jpg',
            'size': photo.file_size
        }
        
        uploaded_files.append(file_info)
        await self.scene.update_key(self.__page_name__, 'uploaded_files', uploaded_files)
        
        msg = await message.answer('✅ Фото добавлено')
        await self.scene.update_message()
        
        try:
            from asyncio import sleep
            await sleep(3)
            await msg.delete()
        except:
            pass
    
    @Page.on_text('all')
    async def document_handler(self, message: Message):
        """Обработка документов и других типов файлов"""
        uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
        
        if len(uploaded_files) >= self.max_files:
            await message.answer(f'❌ Достигнут лимит файлов ({self.max_files})')
            return
        
        file_info = None
        
        # Проверяем тип сообщения
        if message.document:
            doc = message.document
            file_info = {
                'type': 'document',
                'file_id': doc.file_id,
                'file_unique_id': doc.file_unique_id,
                'name': doc.file_name or f'document_{len(uploaded_files) + 1}',
                'size': doc.file_size,
                'mime_type': doc.mime_type
            }
        elif message.video:
            video = message.video
            file_info = {
                'type': 'video',
                'file_id': video.file_id,
                'file_unique_id': video.file_unique_id,
                'name': video.file_name or f'video_{len(uploaded_files) + 1}',
                'size': video.file_size,
                'duration': video.duration
            }
        elif message.photo:
            await self.photo_handler(message)
            return

        if file_info:
            uploaded_files.append(file_info)
            await self.scene.update_key(self.__page_name__, 'uploaded_files', uploaded_files)
            msg = await message.answer(f'✅ {file_info["type"].capitalize()} добавлен')
            await self.scene.update_message()

            try:
                from asyncio import sleep
                await sleep(3)
                await msg.delete()
            except:
                pass
