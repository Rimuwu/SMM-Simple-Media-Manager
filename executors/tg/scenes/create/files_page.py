from asyncio import sleep
from typing import Optional
import io
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from tg.oms import Page
from tg.oms.utils import callback_generator, list_to_inline
from PIL import Image
from modules.logs import executors_logger as logger


class FilesPage(Page):
    """Страница для загрузки и просмотра файлов перед созданием карточки"""
    
    __page_name__ = 'files'

    def __after_init__(self):
        """Инициализация значений по умолчанию"""
        self.max_files = 10  # Максимальное количество файлов
        self.allowed_types = ['photo', 'document', 'video']  # Разрешенные типы файлов

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
        
        # Получаем самую большую версию фото
        photo = message.photo[-1]
        
        file_info = {
            'type': 'photo',
            'file_id': photo.file_id,
            'file_unique_id': photo.file_unique_id,
            'name': f'photo_{len(files) + 1}.jpg',
            'size': photo.file_size
        }
        
        files.append(file_info)
        await self.scene.update_key('scene', 'files', files)
        
        await message.answer('✅ Фото добавлено')
        await self.scene.update_message()

    @Page.on_text('all')
    async def document_handler(self, message: Message):
        """Обработка документов и других типов файлов"""
        files = self.scene.data['scene'].get('files', [])
        
        if len(files) >= self.max_files:
            await message.answer(f'❌ Достигнут лимит файлов ({self.max_files})')
            return
        
        file_info = None
        
        # Проверяем тип сообщения
        if message.document:
            doc = message.document
            mime_type = doc.mime_type or ''
            file_name_orig = doc.file_name or ''
            
            # Проверяем, является ли документ изображением
            image_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff']
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif']
            
            is_image = (
                mime_type in image_mimes or
                any(file_name_orig.lower().endswith(ext) for ext in image_extensions)
            )
            
            if is_image:
                # Конвертируем в фото
                try:
                    file = await self.scene.__bot__.get_file(doc.file_id)
                    if not file.file_path:
                        await message.answer('❌ Не удалось получить файл')
                        return
                        
                    file_data = await self.scene.__bot__.download_file(file.file_path)
                    if not file_data:
                        await message.answer('❌ Не удалось скачать файл')
                        return
                        
                    raw_data = file_data.read()
                    
                    # Конвертируем в JPEG
                    image = Image.open(io.BytesIO(raw_data))
                    if image.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', image.size, (255, 255, 255))
                        if image.mode == 'P':
                            image = image.convert('RGBA')
                        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                        image = background
                    elif image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    output = io.BytesIO()
                    image.save(output, format='JPEG', quality=95)
                    jpeg_data = output.getvalue()
                    
                    # Отправляем как фото и получаем file_id
                    new_photo_name = f'photo_{len(files) + 1}.jpg'
                    photo_file = BufferedInputFile(jpeg_data, filename=new_photo_name)
                    
                    sent_msg = await self.scene.__bot__.send_photo(
                        chat_id=self.scene.user_id,
                        photo=photo_file,
                        caption="🔄 Конвертация документа в фото..."
                    )
                    
                    # Получаем file_id из отправленного фото
                    if not sent_msg.photo:
                        await message.answer('❌ Ошибка конвертации фото')
                        return
                        
                    new_photo = sent_msg.photo[-1]
                    
                    file_info = {
                        'type': 'photo',
                        'file_id': new_photo.file_id,
                        'file_unique_id': new_photo.file_unique_id,
                        'name': new_photo_name,
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
                    file_info = {
                        'type': 'document',
                        'file_id': doc.file_id,
                        'file_unique_id': doc.file_unique_id,
                        'name': doc.file_name or f'document_{len(files) + 1}',
                        'size': doc.file_size,
                        'mime_type': doc.mime_type
                    }
            else:
                # Обычный документ (не изображение)
                file_info = {
                    'type': 'document',
                    'file_id': doc.file_id,
                    'file_unique_id': doc.file_unique_id,
                    'name': doc.file_name or f'document_{len(files) + 1}',
                    'size': doc.file_size,
                    'mime_type': doc.mime_type
                }
        elif message.video:
            video = message.video
            file_info = {
                'type': 'video',
                'file_id': video.file_id,
                'file_unique_id': video.file_unique_id,
                'name': video.file_name or f'video_{len(files) + 1}',
                'size': video.file_size,
                'duration': video.duration
            }
        elif message.photo:
            photos = message.photo
            for photo in photos:
                file_info = {
                    'type': 'photo',
                    'file_id': photo.file_id,
                    'file_unique_id': photo.file_unique_id,
                    'name': f'photo_{len(files) + 1}.jpg',
                    'size': photo.file_size
                }

        if file_info:
            files.append(file_info)
            await self.scene.update_key('scene', 'files', files)
            ms = await message.answer(f'✅ {file_info["type"].capitalize()} добавлен')
            await self.scene.update_message()

            try:
                await sleep(5)  # Небольшая задержка для корректной отправки
                await ms.delete()
            except:
                pass
        else:
            # Если это просто текст - игнорируем
            pass
