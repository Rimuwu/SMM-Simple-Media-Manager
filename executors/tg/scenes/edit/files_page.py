"""
Страница для просмотра и выбора файлов карточки
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram import Bot
from tg.oms import Page
from modules.api_client import brain_api
from global_modules.brain_client import brain_client
from modules.logs import executors_logger as logger
from modules.file_utils import (
    generate_unique_filename,
    download_telegram_file,
    is_image_by_mime_or_extension
)


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
            await self.scene.update_key(self.__page_name__, 'selected_files', [])
            return
        
        # Инициализируем список загруженных файлов если его нет
        if self.scene.get_key(self.__page_name__, 'uploaded_files') is None:
            await self.scene.update_key(self.__page_name__, 'uploaded_files', [])
        
        # Загружаем выбранные файлы из карточки (post_images)
        saved_images = card.get('post_images') or []
        if self.scene.get_key(self.__page_name__, 'selected_files') is None:
            await self.scene.update_key(self.__page_name__, 'selected_files', saved_images)
        
        task_id = card.get('task_id')
        
        try:
            # Запрос файлов карточки из локального файлового API
            response = await brain_client.list_files(card_id=str(card.get('card_id')))
            status = 200 if response else 404

            if status == 200 and response.get('files'):
                files_list = response['files']
                await self.scene.update_key(self.__page_name__, 'files', files_list)

                # Нормализуем выбранные файлы: сохраняем UUID'ы вместо имён
                saved_images = card.get('post_images') or []

                # Маппинг по id и по именам
                id_by_name = {f.get('original_filename') or f.get('name'): str(f.get('id')) for f in files_list}
                ids = []
                for it in saved_images:
                    # если уже id
                    if any(str(f.get('id')) == str(it) for f in files_list):
                        ids.append(str(it))
                    else:
                        # пробуем сопоставить по имени
                        mapped = id_by_name.get(it)
                        if mapped:
                            ids.append(mapped)

                # Если в данных сцены нет selected_files — устанавливаем нормализованное значение
                existing_selected = self.scene.get_key(self.__page_name__, 'selected_files')
                if existing_selected is None:
                    await self.scene.update_key(self.__page_name__, 'selected_files', ids)
                else:
                    # Попробуем нормализовать существующие значения, если это имена
                    normalized = []
                    for it in existing_selected:
                        if any(str(f.get('id')) == str(it) for f in files_list):
                            normalized.append(str(it))
                        else:
                            mapped = id_by_name.get(it)
                            if mapped:
                                normalized.append(mapped)
                    if normalized and normalized != existing_selected:
                        await self.scene.update_key(self.__page_name__, 'selected_files', normalized)

            else:
                await self.scene.update_key(self.__page_name__, 'files', [])
        except Exception as e:
            print(f"Error getting files: {e}")
            await self.scene.update_key(self.__page_name__, 'files', [])
    
    async def content_worker(self) -> str:
        """Возвращает текст сообщения"""
        files = self.scene.get_key(self.__page_name__, 'files') or []
        selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []
        
        add_vars = {
            'kaiten_count': len(files),
            'selected_count': len(selected_files),
            'max_files': self.max_files
        }

        # Формируем список выбранных файлов для отображения (с порядком загрузки)
        if selected_files:
            files_list = []
            # Мап id -> имя
            id_to_name = {str(f.get('id')): f.get('original_filename', f.get('name', 'без имени')) for f in files}
            for idx, file_id in enumerate(selected_files, 1):
                name = id_to_name.get(str(file_id), str(file_id))
                files_list.append(f"📌 {idx}. `{name}`")
            add_vars['selected_files_list'] = '\n'.join(files_list)
        else:
            add_vars['selected_files_list'] = '📭 Нет выбранных файлов'

        # Формируем список файлов карточки (показываем номер в очереди если выбран)
        if files:
            files_list = []
            for idx, file_info in enumerate(files):
                file_id = str(file_info.get('id'))
                file_name = file_info.get('original_filename', file_info.get('name', 'без имени'))
                # Проверяем, выбран ли файл и его позицию в очереди
                if file_id in selected_files:
                    order_num = selected_files.index(file_id) + 1
                    mark = f'✅ {order_num}.'
                else:
                    mark = f'{idx+1}.'

                files_list.append(f"{mark} `{file_name}`")

            add_vars['kaiten_files_list'] = '\n'.join(files_list)
        else:
            add_vars['kaiten_files_list'] = '📭 Нет файлов в карточке' 
        
        return self.append_variables(**add_vars)
    
    async def buttons_worker(self) -> list[dict]:
        """Создает кнопки с файлами"""
        from tg.oms.utils import callback_generator
        
        buttons = []
        files = self.scene.get_key(self.__page_name__, 'files') or []
        selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []
        
        # Получаем сохранённые файлы из карточки для сравнения
        card = await self.scene.get_card_data()
        saved_images = card.get('post_images') or [] if card else []
        # Нормализуем сохранённые значения в UUID'ы, если они были именами
        id_by_name = {f.get('original_filename'): str(f.get('id')) for f in files}
        normalized_saved = []
        for it in saved_images:
            if any(str(f.get('id')) == str(it) for f in files):
                normalized_saved.append(str(it))
            else:
                mapped = id_by_name.get(it)
                if mapped:
                    normalized_saved.append(mapped)

        # Кнопки для файлов карточки (просмотр и toggle выбора)
        for idx, file in enumerate(files):
            file_id = file.get('id')
            file_name = file.get('original_filename', 'Без названия')
            
            # Проверяем выбран ли файл
            is_selected = str(file_id) in selected_files
            mark = '✅' if is_selected else '⬜️'
            
            # Ограничиваем длину имени для кнопки
            display_name = file_name[:25] + "..." if len(file_name) > 28 else file_name
            
            buttons.append({
                'text': f"{mark} {display_name}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'select_file',  # Нажатие показывает превью файла
                    str(idx)
                )
            })
        
        # Проверяем, изменились ли выбранные файлы по сравнению с сохранёнными
        files_changed = set(selected_files) != set(normalized_saved)
        
        # (Сохранение теперь происходит автоматически при выходе со страницы)

        
        # Кнопка очистки выбранных (только если есть выбранные)
        if selected_files:
            buttons.append({
                'text': '🗑 Очистить выбранные',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'clear_selected'
                ),
                'ignore_row': True
            })
        
        return buttons
    
    @Page.on_callback('clear_selected')
    async def clear_selected_handler(self, callback: CallbackQuery, args: list):
        """Очистить выбранные файлы"""
        await self.scene.update_key(self.__page_name__, 'selected_files', [])
        await callback.answer('🗑 Выбранные очищены')
        await self.scene.update_message()

    @Page.on_callback('toggle_select')
    async def toggle_select_handler(self, callback: CallbackQuery, args: list):
        """Toggle выбора загруженного файла (устарело, для совместимости)"""
        if len(args) < 2:
            await callback.answer('❌ Ошибка')
            return
        
        try:
            file_idx = int(args[1])
            uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
            selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []
            
            if file_idx < 0 or file_idx >= len(uploaded_files):
                await callback.answer('❌ Файл не найден')
                return
            
            file_info = uploaded_files[file_idx]
            file_id = file_info.get('file_id')
            
            # Проверяем, выбран ли файл
            existing_idx = next(
                (i for i, f in enumerate(selected_files) if f.get('file_id') == file_id), 
                None
            )
            
            if existing_idx is not None:
                # Убираем из выбранных
                selected_files.pop(existing_idx)
                await callback.answer('❌ Файл убран из выбранных')
            else:
                # Добавляем в выбранные
                if len(selected_files) >= self.max_files:
                    await callback.answer(f'❌ Максимум {self.max_files} файлов')
                    return
                selected_files.append(file_info)
                await callback.answer('✅ Файл добавлен в выбранные')
            
            await self.scene.update_key(self.__page_name__, 'selected_files', selected_files)
            await self.scene.update_message()
            
        except Exception as e:
            print(f"Error toggling select: {e}")
            await callback.answer(f'❌ Ошибка: {str(e)}')
    

    
    @Page.on_callback('view_all_uploaded')
    async def view_all_uploaded_handler(self, callback: CallbackQuery, args: list):
        """Просмотр всех загруженных файлов"""
        uploaded_files = self.scene.get_key(self.__page_name__, 'uploaded_files') or []
        
        if not uploaded_files:
            await callback.answer('📭 Нет загруженных файлов')
            return
        
        # Показываем первый файл
        await self.view_uploaded_handler(callback, ['view_uploaded', '0'])
    
    @Page.on_callback('select_file')
    async def select_file_handler(self, callback: CallbackQuery, args: list):
        """Обработчик выбора файла - показывает превью"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID файла")
            return
        
        file_id = args[1]
        await self.show_file_preview(callback, file_id)
    
    async def show_file_preview(self, callback: CallbackQuery, file_id: str):
        """Показывает превью файла с кнопками добавить/убрать"""
        from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
        from tg.oms.utils import callback_generator
        
        card = await self.scene.get_card_data()
        
        if not card:
            await callback.answer("❌ Карточка не найдена")
            return
        
        task_id = card.get('task_id')
        files = self.scene.get_key(self.__page_name__, 'files') or []
        selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []
        
        # Получаем файл по индексу
        try:
            idx = int(file_id)
        except Exception:
            await callback.answer("❌ Ошибка: неверный индекс файла")
            return

        if idx < 0 or idx >= len(files):
            await callback.answer("❌ Файл не найден")
            return

        target_file = files[idx]
        file_id_str = str(target_file.get('id'))
        file_name = target_file.get('original_filename', target_file.get('name', 'Без имени'))
        is_selected = file_id_str in selected_files

        try:
            # Получаем бинарные данные файла через локальный endpoint
            file_data, status = await brain_client.download_file(file_id_str)
            
            if status == 200 and isinstance(file_data, bytes):
                # Определяем текст и callback кнопки в зависимости от состояния
                if is_selected:
                    toggle_text = "❌ Убрать из выбранных"
                    toggle_action = "toggle_remove"
                else:
                    toggle_text = "✅ Добавить к выбранным"
                    toggle_action = "toggle_add"
                
                # Создаем кнопки
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=toggle_text,
                            callback_data=callback_generator(
                                self.scene.__scene_name__,
                                toggle_action,
                                str(idx)
                            )
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🗑 Удалить сообщение",
                            callback_data="delete_message"
                        )
                    ]
                ])
                
                # Отправляем фото
                photo = BufferedInputFile(file_data, filename="preview.png")
                status_text = "✅ Выбран" if is_selected else "⬜️ Не выбран"
                await callback.message.answer_photo(
                    photo=photo,
                    caption=f"📷 {file_name}\n\nСтатус: {status_text}",
                    reply_markup=keyboard
                )
                await callback.answer()
            else:
                await callback.answer("❌ Ошибка при загрузке файла")
        
        except Exception as e:
            print(f"Error showing preview: {e}")
            await callback.answer("❌ Произошла ошибка")
    
    @Page.on_callback('toggle_add')
    async def toggle_add_handler(self, callback: CallbackQuery, args: list):
        """Добавить файл к выбранным (использует индекс файла)"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка")
            return
        try:
            idx = int(args[1])
        except Exception:
            await callback.answer("❌ Ошибка: неверный индекс")
            return

        files = self.scene.get_key(self.__page_name__, 'files') or []
        selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []

        if idx < 0 or idx >= len(files):
            await callback.answer("❌ Файл не найден")
            return

        target_file = files[idx]
        file_id = str(target_file.get('id'))
        file_name = target_file.get('original_filename', target_file.get('name', ''))

        if file_id in selected_files:
            await callback.answer("⚠️ Уже добавлен")
            return

        if len(selected_files) >= self.max_files:
            await callback.answer(f"❌ Максимум {self.max_files} файлов")
            return

        selected_files.append(file_id)
        await self.scene.update_key(self.__page_name__, 'selected_files', selected_files)
        await callback.answer(f"✅ Добавлен: {file_name[:30]}")

        # Удаляем сообщение с превью
        try:
            await callback.message.delete()
        except:
            pass
        await self.scene.update_message()
    
    @Page.on_callback('toggle_remove')
    async def toggle_remove_handler(self, callback: CallbackQuery, args: list):
        """Убрать файл из выбранных (использует индекс файла)"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка")
            return
        try:
            idx = int(args[1])
        except Exception:
            await callback.answer("❌ Ошибка: неверный индекс")
            return

        files = self.scene.get_key(self.__page_name__, 'files') or []
        selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []

        if idx < 0 or idx >= len(files):
            await callback.answer("❌ Файл не найден")
            return

        target_file = files[idx]
        file_id = str(target_file.get('id'))
        file_name = target_file.get('original_filename', target_file.get('name', ''))

        if file_id not in selected_files:
            await callback.answer("⚠️ Не был добавлен")
            return

        selected_files.remove(file_id)
        await self.scene.update_key(self.__page_name__, 'selected_files', selected_files)
        await callback.answer(f"❌ Убран: {file_name[:30]}")

        # Удаляем сообщение с превью
        try:
            await callback.message.delete()
        except:
            pass
        await self.scene.update_message()

    @Page.on_callback('confirm_file')
    async def confirm_file_handler(self, callback: CallbackQuery, args: list):
        """Обработчик подтверждения установки файла (устарело)"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID файла")
            return
        
        file_id = args[1]
        await self.toggle_add_handler(callback, args)  # Используем toggle_add
    
    @Page.on_callback('toggle_kaiten')
    async def toggle_kaiten_handler(self, callback: CallbackQuery, args: list):
        """Toggle выбора файла - теперь открывает превью"""
        await self.select_file_handler(callback, args)
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
            success = await brain_client.update_card(
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
            file_name = file_info.get('original_filename', 'файл')

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
            
            await callback.answer(f'✅ Файл "{deleted_file.get("original_filename", "")}" удален')
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
            success = await brain_client.update_card(
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
    
    async def page_leave(self) -> None:
        """Сохраняем выбранные файлы (UUID) в карточку при выходе со страницы"""
        try:
            selected_files = self.scene.get_key(self.__page_name__, 'selected_files') or []
            card = await self.scene.get_card_data()
            if not card:
                return
            card_id = card.get('card_id')
            if not card_id:
                return
            # Сохраняем список UUID файлов в поле post_images для карточки
            await brain_client.update_card(card_id=card_id, post_images=selected_files)
            logger.info(f"Saved selected files for card {card_id}: {selected_files}")
        except Exception as e:
            logger.error(f"Error saving selected files on page leave: {e}")

    async def photo_handler(self, message: Message) -> None:
        """Обработка фотографий - загружает в карточку"""
        card = await self.scene.get_card_data()
        if not card:
            await message.answer('❌ Карточка не найдена')
            return
        
        card_id = card.get('card_id')
        if not card_id:
            await message.answer('❌ ID карточки не найден')
            return
        
        if not message.photo:
            return
        
        # Получаем самую большую версию фото
        photo = message.photo[-1]
        
        try:
            # Скачиваем фото через общую функцию
            file_bytes = await download_telegram_file(self.scene.__bot__, photo.file_id)
            if not file_bytes:
                await message.answer('❌ Не удалось скачать файл')
                return
            
            file_name = f'photo_{message.message_id}.png'
            
            # Загружаем через brain-api upload endpoint
            try:
                converted = brain_client._convert_to_png(file_bytes) if is_image_by_mime_or_extension('image/png', file_name) else file_bytes
            except Exception:
                converted = file_bytes

            res = await brain_client.upload_file(card_id=card_id, file_data=converted, filename=file_name, content_type='image/png')

            if res:
                logger.info(f"Фото {file_name} загружено в карточку {card_id}")
                msg = await message.answer('✅ Фото загружено!')

                # Обновляем список файлов
                await self.data_preparate()
                await self.scene.update_message()

                try:
                    from asyncio import sleep
                    await sleep(3)
                    await msg.delete()
                except:
                    pass
            else:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='🗑 Удалить', callback_data='delete_message')]
                ])
                await message.answer('❌ Ошибка загрузки файла', reply_markup=keyboard)
        
        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await message.answer(f'❌ Ошибка: {str(e)[:100]}')
    
    @Page.on_text('all')
    async def document_handler(self, message: Message):
        """Обработка документов и других типов файлов - загружаем"""
        print(f"[FilesPage] document_handler called. photo={message.photo}, document={message.document}, video={message.video}")
        
        # Фото обрабатываем отдельно
        if message.photo:
            print(f"[FilesPage] Processing photo message")
            await self.photo_handler(message)
            return
        
        # Определяем тип файла и получаем file_id
        file_id = None
        file_name = None
        mime_type = None
        
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or f'document_{file_id[:8]}'
            mime_type = message.document.mime_type
        elif message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or f'video_{file_id[:8]}.mp4'
            mime_type = message.video.mime_type or 'video/mp4'
        
        if not file_id:
            return
        
        try:
            # Получаем card_id (не task_id!)
            card = await self.scene.get_card_data()
            card_id = card.get('card_id')
            
            if not card_id:
                await message.answer('❌ Не найден ID карточки')
                return
            
            # Скачиваем файл из Telegram через общую функцию
            file_bytes = await download_telegram_file(self.scene.__bot__, file_id)
            if not file_bytes:
                await message.answer('❌ Не удалось скачать файл')
                return
            
            # Определяем нужно ли конвертировать в PNG
            is_image = is_image_by_mime_or_extension(mime_type, file_name)
            
            logger.info(f"Загрузка файла {file_name} для карточки {card_id}")
            
            # Загружаем через brain-api upload endpoint
            try:
                converted = brain_client._convert_to_png(file_bytes) if is_image else file_bytes
            except Exception:
                converted = file_bytes

            content_type = 'image/png' if is_image else (mime_type or 'application/octet-stream')
            res = await brain_client.upload_file(card_id=card_id, file_data=converted, filename=file_name or 'file', content_type=content_type)

            if res:
                logger.info(f"Файл {file_name} успешно загружен в карточку {card_id}")
                msg = await message.answer('✅ Файл загружен')

                # Обновляем список файлов
                await self.data_preparate()
                await self.scene.update_message()

                try:
                    from asyncio import sleep
                    await sleep(3)
                    await msg.delete()
                except:
                    pass
            else:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='🗑 Удалить', callback_data='delete_message')]
                ])
                await message.answer('❌ Ошибка загрузки файла', reply_markup=keyboard)
        
        except Exception as e:
            logger.error(f"Ошибка обработки файла: {e}")
            await message.answer(f'❌ Ошибка: {str(e)[:100]}')
