"""
Страница для просмотра и выбора файлов карточки (упрощённая версия)
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, BufferedInputFile
from tg.oms import Page
from app.models.card.Card import Card
from app.models.task.TaskFile import CardFile
from app.modules.components.logs import logger
from modules.file_utils import download_telegram_file, is_image_by_mime_or_extension, is_video_by_mime_or_extension, detect_file_type_by_bytes, convert_image_to_png
from app.modules.components.storage import download_file as _dl_storage
from uuid import UUID as _UUID


class FilesPage(Page):
    __page_name__ = 'files-view'
    __can_select__ = True

    def __after_init__(self):
        self.max_files = 10

    async def _card(self):
        return await self.scene.get_card_data()

    async def _files(self):
        return self.scene.get_key(self.__page_name__, 'files') or []

    async def _selected(self):
        return self.scene.get_key(self.__page_name__, 'selected_files') or []

    async def _set_selected(self, val):
        await self.scene.update_key(self.__page_name__, 'selected_files', val)

    async def data_preparate(self):
        card = await self._card()
        if not card:
            for k in ('files', 'uploaded_files', 'selected_files'):
                await self.scene.update_key(self.__page_name__, k, [])
            return

        if self.scene.get_key(self.__page_name__, 'uploaded_files') is None:
            await self.scene.update_key(self.__page_name__, 'uploaded_files', [])

        saved = card.get('post_images') or []
        if self.scene.get_key(self.__page_name__, 'selected_files') is None:
            await self.scene.update_key(self.__page_name__, 'selected_files', saved)

        try:
            files = [f.to_dict() for f in await CardFile.for_card(str(card.get('card_id')))]
            files = files if files else []
            await self.scene.update_key(self.__page_name__, 'files', files)

            # Normalize selected -> ids
            id_by_name = {
                f.get('original_filename') or f.get('name'): str(f.get('id')) for f in files
                }
            cur = self.scene.get_key(self.__page_name__, 'selected_files') or []
            normalized = [
                str(it) if any(str(f.get('id')) == str(it) for f in files) else id_by_name.get(it) for it in cur
                ]
            normalized = [i for i in normalized if i]
            if normalized and normalized != cur:
                await self._set_selected(normalized)
        except Exception as e:
            logger.debug('Error getting files: %s', e)
            await self.scene.update_key(self.__page_name__, 'files', [])

    async def content_worker(self) -> str:
        files = await self._files()
        sel = await self._selected()
        id_to_name = {str(f.get('id')): f.get('original_filename', f.get('name', 'без имени')) for f in files}

        # Список выбранных файлов (с порядком)
        selected_files_list_lines = []
        for i, fid in enumerate(sel, 1):
            name = id_to_name.get(str(fid), str(fid))
            selected_files_list_lines.append(f"📌 {i}. `{name}`")
        selected_files_list = '\n'.join(selected_files_list_lines) if selected_files_list_lines else '📭 Нет выбранных файлов'

        # Список файлов карточки (с отметкой и порядком если выбран)
        kaiten_files_list_lines = []
        for idx, f in enumerate(files):
            fid = str(f.get('id'))
            fname = f.get('original_filename', f.get('name', 'без имени'))
            if fid in sel:
                order = sel.index(fid) + 1
                mark = f"✅ {order}."
            else:
                mark = f"{idx+1}."
            kaiten_files_list_lines.append(f"{mark} `{fname}`")
        kaiten_files_list = '\n'.join(kaiten_files_list_lines) if kaiten_files_list_lines else '📭 Нет файлов в карточке'

        add_vars = {
            'kaiten_count': len(files),
            'selected_count': len(sel),
            'max_files': self.max_files,
            'selected_files_list': selected_files_list,
            'kaiten_files_list': kaiten_files_list
        }
        return self.append_variables(**add_vars)

    async def buttons_worker(self) -> list[dict]:
        from tg.oms.utils import callback_generator
        files = await self._files()
        sel = await self._selected()
        buttons = []
        for idx, f in enumerate(files):
            name = f.get('original_filename', 'Без названия')
            mark = '✅' if str(f.get('id')) in sel else '⬜️'
            display = name if len(name) <= 28 else name[:25] + '...'
            buttons.append(
                {'text': f"{mark} {display}", 
                 'callback_data': callback_generator(self.scene.__scene_name__, 'select_file', str(idx))})
        if sel:
            from tg.oms.utils import callback_generator
            buttons.append(
                {'text': '🗑 Очистить выбранные', 
                 'callback_data': callback_generator(self.scene.__scene_name__, 'clear_selected'), 
                 'ignore_row': True})
        return buttons

    async def _file_by_idx(self, idx: int):
        files = await self._files()
        if idx < 0 or idx >= len(files):
            return None
        return files[idx]

    @Page.on_callback('clear_selected')
    async def clear_selected_handler(self, callback: CallbackQuery, args: list):
        await self._set_selected([])
        await callback.answer('🗑 Выбранные очищены')
        await self.scene.update_message()

    @Page.on_callback('select_file')
    async def select_file_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            return await callback.answer('❌ Ошибка: не указан ID файла')
        try:
            idx = int(args[1])
        except Exception:
            return await callback.answer('❌ Ошибка: неверный индекс')
        await self.show_file_preview(callback, idx)

    async def show_file_preview(self, 
                    callback: CallbackQuery, idx: int):
        from tg.oms.utils import callback_generator
        card = await self._card()
        if not card:
            return await callback.answer('❌ Карточка не найдена')
        target = await self._file_by_idx(idx)
        if not target:
            return await callback.answer('❌ Файл не найден')

        fid = str(target.get('id'))
        sel = await self._selected()
        is_selected = fid in sel
        is_hidden = target.get('hide', False)
        
        try:
            cf = await CardFile.get_by_id(_UUID(str(fid)))
            file_data, status = (await _dl_storage(cf.filename)) if cf else (None, 404)
            if status != 200 or not isinstance(file_data, bytes):
                return await callback.answer('❌ Ошибка при загрузке файла')

            toggle_action = 'toggle_remove' if is_selected else 'toggle_add'
            toggle_text = '❌ Убрать из выбранных' if is_selected else '✅ Добавить к выбранным'

            hide_emoji = '👁️' if is_hidden else '🙈'
            hide_text = f'{hide_emoji} {"Показать" if is_hidden else "Скрыть"}'

            buttons = []

            if self.__can_select__:
                buttons.append([
                    InlineKeyboardButton(
                        text=toggle_text, 
                        callback_data=callback_generator(
                            self.scene.__scene_name__, 
                            toggle_action, str(idx))
                        )
                ])
            
            # Кнопка для переключения hide
            buttons.append([
                InlineKeyboardButton(
                    text=hide_text,
                    callback_data=callback_generator(
                        self.scene.__scene_name__,
                        'toggle_hide', str(idx))
                )
            ])

            buttons.append([
                InlineKeyboardButton(
                    text='🗑 Закрыть сообщение',
                    callback_data='delete_message',
                    style='primary'
                )
            ])
            

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=buttons
            )
            
            hide_status_text = f"\nСкрыт: 🙈 {'Да' if is_hidden else 'Нет'}"
            selection_status = f"✅ Выбран" if is_selected else "⬜️ Не выбран"

            # Определяем тип файла (video или image) по MIME/имени/байтам
            mime = None
            data_info = target.get('data_info') or {}
            mime = data_info.get('mime_type') or target.get('mime_type') or ''
            original_name = target.get('original_filename') or target.get('name') or ''

            is_video = is_video_by_mime_or_extension(mime, original_name)

            # Фоллбек: если mime/имя не дают ответа — определим по байтам
            if not is_video:
                try:
                    _mime, _ext, ftype = detect_file_type_by_bytes(file_data)
                    is_video = (ftype == 'video')
                except Exception:
                    is_video = False

            caption_text = f"{('🎬' if is_video else '📷')} {target.get('original_filename', target.get('name', 'Без имени'))}\n\nСтатус: {selection_status}{hide_status_text}"

            if is_video:
                # Подбираем корректное имя файла с расширением
                if '.' in original_name:
                    fname = original_name
                else:
                    try:
                        _mime, ext, _ = detect_file_type_by_bytes(file_data)
                        fname = f'preview{ext or ".mp4"}'
                    except Exception:
                        fname = 'preview.mp4'

                await callback.message.answer_video(
                    video=BufferedInputFile(file_data, filename=fname),
                    caption=caption_text,
                    reply_markup=keyboard,
                    has_spoiler=is_hidden
                )
            else:
                await callback.message.answer_photo(
                    photo=BufferedInputFile(file_data, filename='preview.png'),
                    caption=caption_text,
                    reply_markup=keyboard,
                    has_spoiler=is_hidden
                )
        
        except Exception as e:
            logger.error(f'Error showing file preview: {e}')
            await callback.answer('❌ Произошла ошибка при отображении файла')

    @Page.on_callback('toggle_hide')
    async def toggle_hide_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            return await callback.answer('❌ Ошибка: файл не найден')
        try:
            idx = int(args[1])
        except Exception:
            return await callback.answer('❌ Ошибка: неверный индекс')
        
        files = await self._files()
        if idx < 0 or idx >= len(files):
            return await callback.answer('❌ Файл не найден')
        
        f = files[idx]
        file_id = str(f.get('id'))
        
        try:
            # Переключаем hide
            cf = await CardFile.get_by_id(_UUID(str(file_id)))
            result = None
            if cf:
                await cf.update(hide=not cf.hide)
                result = cf.to_dict()
            if result:
                new_hide = result.get('hide', False)
                status_text = 'скрыт' if new_hide else 'показан'
                await callback.answer(f'✅ Файл {status_text}')
                
                # Обновляем данные
                await self.data_preparate()
                await self.scene.update_message()
                
                # Удаляем превью сообщение
                try:
                    await callback.message.delete()
                except:
                    pass
            else:
                await callback.answer('❌ Ошибка при изменении статуса')
        except Exception as e:
            logger.error(f'Error toggling hide: {e}')
            await callback.answer('❌ Произошла ошибка')

    async def page_leave(self) -> None:
        try:
            sel = await self._selected()
            card = await self._card()
            if card and card.get('card_id'):
                card_obj = await Card.get_by_id(_UUID(str(card.get('card_id'))))
                if card_obj:
                    await card_obj.update(post_images=sel)
                logger.info('Saved selected files for card %s: %s', card.get('card_id'), sel)
        except Exception as e:
            logger.error('Error saving selected files on page leave: %s', e)

    async def _upload_common(self, message: Message, file_id: str, filename: str, mime: str | None):
        card = await self._card()
        if not card or not card.get('card_id'):
            return await message.answer('❌ Карточка не найдена')
        data = await download_telegram_file(self.scene.__bot__, file_id)
        if not data:
            return await message.answer('❌ Не удалось скачать файл')
        try:
            converted = convert_image_to_png(data) if is_image_by_mime_or_extension(mime, filename) else data
        except Exception:
            converted = data
    
        content_type = 'image/png' if is_image_by_mime_or_extension(mime, filename) else (mime or 'application/octet-stream')
        res = await CardFile.upload(
            card_id=card.get('card_id'), 
            file_data=converted,
            filename=filename or 'file', 
            content_type=content_type
        )

        if res:
            msg = await message.answer('✅ Файл загружен')
            await self.data_preparate()
            await self.scene.update_message()
            try:
                from asyncio import sleep
                await sleep(3)
                await msg.delete()
                await message.delete()
            except:
                pass
        else:
            await message.answer('❌ Ошибка загрузки файла', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🗑 Удалить', callback_data='delete_message')]]))

    async def photo_handler(self, message: Message) -> None:
        if not message.photo:
            return
        photo = message.photo[-1]
        await self._upload_common(message, photo.file_id, f'photo_{message.message_id}.png', 'image/png')

    @Page.on_text('all')
    async def document_handler(self, message: Message):
        if message.photo:
            return await self.photo_handler(message)
        file_id, filename, mime = None, None, None

        if message.document:
            file_id = message.document.file_id; filename = message.document.file_name or f'document_{file_id[:8]}'; mime = message.document.mime_type
    
        elif message.video:
            file_id = message.video.file_id; filename = message.video.file_name or f'video_{file_id[:8]}.mp4'; mime = message.video.mime_type or 'video/mp4'

        if not file_id:
            return
        await self._upload_common(message, file_id, 
                                  filename, mime)
    
    async def _toggle_selected_by_idx(self, idx: int, add: bool):
        target = await self._file_by_idx(idx)
        if not target:
            return None, '❌ Файл не найден'
        fid = str(target.get('id'))
        sel = await self._selected()

        if add:
            if fid in sel:
                return None, '⚠️ Уже добавлен'
            if len(sel) >= self.max_files:
                return None, f'❌ Максимум {self.max_files} файлов'
            sel.append(fid)

        else:
            if fid not in sel:
                return None, '⚠️ Не был добавлен'
            sel.remove(fid)
        await self._set_selected(sel)
        return target, None

    @Page.on_callback('toggle_add')
    async def toggle_add_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            return await callback.answer('❌ Ошибка')
        try:
            idx = int(args[1])
        except Exception:
            return await callback.answer('❌ Ошибка: неверный индекс')
        target, err = await self._toggle_selected_by_idx(idx, True)
        if err:
            return await callback.answer(err)
        await callback.answer(f"✅ Добавлен: {target.get('original_filename', '')[:30]}")

        try: await callback.message.delete()
        except: pass
        await self.scene.update_message()

    @Page.on_callback('toggle_remove')
    async def toggle_remove_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            return await callback.answer('❌ Ошибка')
        try:
            idx = int(args[1])
        except Exception:
            return await callback.answer('❌ Ошибка: неверный индекс')

        target, err = await self._toggle_selected_by_idx(idx, False)
        if err:
            return await callback.answer(err)
        await callback.answer(f"❌ Убран: {target.get('original_filename', '')[:30]}")
    
        try: await callback.message.delete()
        except: pass
        await self.scene.update_message()