from asyncio import sleep
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from tg.oms import Page
from tg.oms.utils import callback_generator, list_to_inline
from app.modules.components.logs import logger
from modules.file_utils import (
    generate_unique_filename,
    is_image_by_mime_or_extension,
    download_telegram_file,
    convert_image_to_png
)


class FilesPage(Page):
    """Страница для загрузки и просмотра файлов перед созданием карточки"""

    __page_name__ = 'files'

    def __after_init__(self):
        """Инициализация значений по умолчанию"""
        self.max_files = 10  # Максимальное количество файлов
        self.allowed_types = ['photo', 'document', 'video']  # Разрешенные типы файлов

    def _get_existing_names(self, files: list) -> set:
        """Получает множество существующих имён файлов"""
        return {f.get('name', '') for f in files}

    async def data_preparate(self) -> None:
        """Подготовка данных страницы"""
        # Инициализируем список файлов если его нет
        if 'files' not in self.scene.data['scene']:
            await self.scene.update_key('scene', 'files', [])

    async def content_worker(self) -> str:
        """Генерация контента страницы"""
        self.clear_content()
        files = self.scene.data['scene'].get('files', [])
        
        add_vars = {
            'files_count': len(files),
            'max_files': self.max_files
        }
        
        # Формируем список файлов для отображения
        if files:
            files_list = []
            for idx, file_info in enumerate(files, 1):
                file_type = file_info.get('type', 'файл')
                file_name = file_info.get('name', 'без имени')
                files_list.append(f"{idx}. {file_type}: `{file_name}`")
            add_vars['files_list'] = '\n'.join(files_list)
        else:
            add_vars['files_list'] = '📭 Файлы не добавлены'
        
        return self.append_variables(**add_vars)

    async def buttons_worker(self) -> list[dict]:
        """Генерация кнопок"""
        buttons = []
        files = self.scene.data['scene'].get('files', [])
        
        # Кнопки для просмотра файлов
        if files:
            for idx, file_info in enumerate(files):
                buttons.append({
                    'text': f'👁 Просмотр {idx + 1}',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'view_file',
                        str(idx)
                    )
                })
            
            # Кнопка очистки всех файлов
            buttons.append({
                'text': '🗑 Очистить все',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'clear_files'
                ),
                'ignore_row': True
            })
        
        return buttons

    @Page.on_callback('view_file')
    async def view_file_handler(self, callback: CallbackQuery, args: list):
        """Просмотр конкретного файла"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка: файл не найден')
            return
        
        try:
            file_idx = int(args[1])
            files = self.scene.data['scene'].get('files', [])
            
            if file_idx < 0 or file_idx >= len(files):
                await callback.answer('❌ Файл не найден')
                return
            
            file_info = files[file_idx]
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
                        'delete_file',
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

        except Exception as e:
            await callback.answer(f'❌ Ошибка: {str(e)}')

    @Page.on_callback('delete_file')
    async def delete_file_handler(self, callback: CallbackQuery, args: list):
        """Удаление конкретного файла"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка: файл не найден')
            return
        
        try:
            file_idx = int(args[1])
            files = self.scene.data['scene'].get('files', [])
            
            if file_idx < 0 or file_idx >= len(files):
                await callback.answer('❌ Файл не найден')
                return
            
            # Удаляем файл из списка
            deleted_file = files.pop(file_idx)
            await self.scene.update_key('scene', 'files', files)
            
            ms = await callback.answer(f'✅ Файл "{deleted_file.get("name", "")}" удален')
            await self.scene.update_message()
            try:
                await callback.message.delete()
                # await sleep(5)
            except:
                pass
            
        except Exception as e:
            await callback.answer(f'❌ Ошибка: {str(e)}')

    @Page.on_callback('clear_files')
    async def clear_files_handler(self, callback: CallbackQuery, args: list):
        """Очистка всех файлов"""
        await self.scene.update_key('scene', 'files', [])
        await callback.answer('✅ Все файлы удалены')
        await self.scene.update_message()

    async def photo_handler(self, message: Message) -> None:
        """Обработка фотографий"""
        files = self.scene.data['scene'].get('files', [])

        if len(files) >= self.max_files:
            await message.answer(f'❌ Достигнут лимит файлов ({self.max_files})')
            return

        if not message.photo:
            return

        # Информируем пользователя о начале загрузки
        ms = await message.answer('🔄 Загрузка файла...')

        try:
            # Получаем самую большую версию фото
            photo = message.photo[-1]

            # Генерируем уникальное имя
            base_name = 'photo.png'
            existing_names = self._get_existing_names(files)
            unique_name = generate_unique_filename(base_name, existing_names)

            file_info = {
                'type': 'photo',
                'file_id': photo.file_id,
                'file_unique_id': photo.file_unique_id,
                'name': unique_name,
                'size': photo.file_size
            }

            files.append(file_info)
            await self.scene.update_key('scene', 'files', files)
            await self.scene.update_message()

            # Обновляем сообщение о загрузке и удаляем оба сообщения
            try:
                await ms.edit_text('✅ Фото добавлено')
            except:
                pass

            try:
                await sleep(2)
                await ms.delete()
            except:
                pass

            try:
                await message.delete()
            except:
                pass

        except Exception as e:
            try:
                await ms.edit_text(f'❌ Ошибка: {str(e)}')
            except:
                pass
            try:
                await sleep(3)
                await ms.delete()
            except:
                pass
            try:
                await message.delete()
            except:
                pass

    @Page.on_text('all')
    async def document_handler(self, message: Message):
        """Обработка документов и других типов файлов"""
        files = self.scene.data['scene'].get('files', [])

        if len(files) >= self.max_files:
            await message.answer(f'❌ Достигнут лимит файлов ({self.max_files})')
            return

        file_info = None
        existing_names = self._get_existing_names(files)

        # Если сообщение содержит файл — показываем сообщение о начале загрузки
        ms = None
        if message.document or message.video or message.photo:
            ms = await message.answer('🔄 Начинаю загрузку...')

        try:
            # Проверяем тип сообщения
            if message.document:
                doc = message.document
                mime_type = doc.mime_type or ''
                file_name_orig = doc.file_name or ''

                # Проверяем, является ли документ изображением
                is_image = is_image_by_mime_or_extension(mime_type, file_name_orig)

                if is_image:
                    # Конвертируем в PNG
                    try:
                        raw_data = await download_telegram_file(self.scene.__bot__, doc.file_id)
                        if not raw_data:
                            if ms:
                                await ms.edit_text('❌ Не удалось скачать файл')
                                await sleep(2)
                                try: await ms.delete()
                                except: pass
                            return

                        # Конвертируем в PNG
                        png_data = convert_image_to_png(raw_data)

                        # Отправляем как фото и получаем file_id
                        if file_name_orig:
                            if '.' in file_name_orig:
                                base_name = file_name_orig.rsplit('.', 1)[0] + '.png'
                            else:
                                base_name = file_name_orig + '.png'
                        else:
                            base_name = 'photo.png'

                        unique_name = generate_unique_filename(base_name, existing_names)
                        photo_file = BufferedInputFile(png_data, filename=unique_name)

                        sent_msg = await self.scene.__bot__.send_photo(
                            chat_id=self.scene.user_id,
                            photo=photo_file,
                            caption="🔄 Конвертация документа в фото..."
                        )

                        # Получаем file_id из отправленного фото
                        if not sent_msg.photo:
                            if ms:
                                await ms.edit_text('❌ Ошибка конвертации фото')
                                await sleep(2)
                                try: await ms.delete()
                                except: pass
                            return

                        new_photo = sent_msg.photo[-1]

                        file_info = {
                            'type': 'photo',
                            'file_id': new_photo.file_id,
                            'file_unique_id': new_photo.file_unique_id,
                            'name': unique_name,
                            'size': new_photo.file_size
                        }

                        # Удаляем техническое сообщение
                        try:
                            await sent_msg.delete()
                        except:
                            pass

                        logger.info(f"Документ {file_name_orig} конвертирован в фото")

                    except Exception as e:
                        logger.error(f"Ошибка конвертации документа в фото: {e}")
                        # Если конвертация не удалась, сохраняем как документ
                        fallback_name = doc.file_name or 'document'
                        unique_fallback_name = generate_unique_filename(fallback_name, existing_names)

                        file_info = {
                            'type': 'document',
                            'file_id': doc.file_id,
                            'file_unique_id': doc.file_unique_id,
                            'name': unique_fallback_name,
                            'size': doc.file_size,
                            'mime_type': doc.mime_type
                        }
                else:
                    # Обычный документ (не изображение)
                    base_name = doc.file_name or 'document'
                    unique_name = generate_unique_filename(base_name, existing_names)

                    file_info = {
                        'type': 'document',
                        'file_id': doc.file_id,
                        'file_unique_id': doc.file_unique_id,
                        'name': unique_name,
                        'size': doc.file_size,
                        'mime_type': doc.mime_type
                    }
            elif message.video:
                video = message.video
                base_name = video.file_name or 'video.mp4'
                unique_name = generate_unique_filename(base_name, existing_names)

                file_info = {
                    'type': 'video',
                    'file_id': video.file_id,
                    'file_unique_id': video.file_unique_id,
                    'name': unique_name,
                    'size': video.file_size,
                    'duration': video.duration
                }

            elif message.photo:
                photos = message.photo
                photo = photos[-1]  # Берём самое большое фото

                base_name = 'photo.png'
                unique_name = generate_unique_filename(base_name, existing_names)

                file_info = {
                    'type': 'photo',
                    'file_id': photo.file_id,
                    'file_unique_id': photo.file_unique_id,
                    'name': unique_name,
                    'size': photo.file_size
                }

            if file_info:
                files.append(file_info)
                await self.scene.update_key('scene', 'files', files)
                await self.scene.update_message()

                # Обновляем сообщение о загрузке и удаляем оба сообщения
                try:
                    if ms:
                        await ms.edit_text(f'✅ {file_info["type"].capitalize()} добавлен')
                    else:
                        ms = await message.answer(f'✅ {file_info["type"].capitalize()} добавлен')
                except:
                    pass

                try:
                    await sleep(2)
                    if ms:
                        await ms.delete()
                except:
                    pass

                try:
                    await message.delete()
                except:
                    pass
            else:
                # Если это просто текст - игнорируем
                pass

        except Exception as e:
            if ms:
                try:
                    await ms.edit_text(f'❌ Ошибка: {str(e)}')
                    await sleep(3)
                    await ms.delete()
                except:
                    pass
            else:
                try:
                    await message.answer(f'❌ Ошибка: {str(e)}')
                except:
                    pass
