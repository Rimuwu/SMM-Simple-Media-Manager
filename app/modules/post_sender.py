"""
Модуль для отправки постов и превью.
Используется в preview_page, post.py и других местах.
Поддерживает фото, видео и media group.
"""
from typing import Optional, Union
from aiogram import Bot
from aiogram.types import (
    BufferedInputFile, 
    InputMediaPhoto, 
    InputMediaVideo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)
from modules.entities_sender import get_entities_for_client, send_poll_preview
from uuid import UUID as _UUID
from models.CardFile import CardFile
from modules.storage import download_file as _storage_download_file
from modules.post_generator import generate_post, render_post_from_card
from modules.logs import logger


def detect_media_type(file_data: bytes, file_name: str = '') -> str:
    """
    Определяет тип медиа по magic bytes и расширению.
    
    Returns:
        'photo', 'video' или 'unknown'
    """
    # По magic bytes
    if len(file_data) >= 12:
        # Видео форматы
        if file_data[4:8] == b'ftyp':  # MP4, MOV, etc.
            return 'video'
        if file_data[:4] == b'\x1aE\xdf\xa3':  # WebM/MKV
            return 'video'
        if file_data[:4] == b'RIFF' and file_data[8:12] == b'AVI ':  # AVI
            return 'video'
        
        # Изображения
        if file_data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'photo'
        if file_data[:2] == b'\xff\xd8':
            return 'photo'
        if file_data[:6] in (b'GIF87a', b'GIF89a'):
            return 'photo'
        if file_data[:4] == b'RIFF' and file_data[8:12] == b'WEBP':
            return 'photo'
    
    # По расширению
    if file_name:
        ext = file_name.lower().rsplit('.', 1)[-1] if '.' in file_name else ''
        if ext in ('mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v'):
            return 'video'
        if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
            return 'photo'
    
    return 'unknown'


async def download_files(file_ids: list[str]) -> list[dict]:
    """
    Скачать файлы по их ID из БД (через brain_client).

    Args:
        file_ids: Список идентификаторов файлов (ID в БД)

    Returns:
        Список словарей: [{'id': str, 'data': bytes, 'name': str, 'type': str, 'hide': bool}, ...]
    """
    if not file_ids:
        return []

    downloaded_files: list[dict] = []

    for file_ref in file_ids:
        try:
            file_id = str(file_ref)

            cf = await CardFile.get_by_id(_UUID(file_id))
            if not cf:
                logger.warning(f"File record not found: {file_id}")
                continue

            file_data, status = await _storage_download_file(cf.filename)
            if status == 200 and isinstance(file_data, (bytes, bytearray)):
                file_name = cf.original_filename or cf.filename
                media_type = detect_media_type(file_data, file_name)
                downloaded_files.append({'id': file_id, 'data': file_data, 'name': file_name,
                                         'type': media_type, 'hide': cf.hide})
                logger.info(f"Downloaded file '{file_name}' ({len(file_data)} bytes, type: {media_type})")
            else:
                logger.warning(f"Failed to download file {file_ref}: status={status}")
        except Exception as e:
            logger.error(f"Error downloading file {file_ref}: {e}", exc_info=True)

    return downloaded_files


async def send_post_preview(
    bot: Bot,
    chat_id: int,
    text: str,
    media_files: Optional[list[dict]] = None,
    parse_mode: str = "html",
    entities: Optional[list] = None
) -> dict:
    """
    Отправляет пост (превью) в чат с поддержкой фото, видео и media group.
    
    Args:
        bot: Telegram Bot instance
        chat_id: ID чата для отправки
        text: Текст поста
        media_files: Список файлов [{'data': bytes, 'name': str, 'type': str}, ...]
        parse_mode: Режим парсинга текста
        with_delete_button: Добавить кнопку удаления сообщения
    
    Returns:
        {'success': bool, 'message_ids': list[int], 'error': str | None}
    """
    try:
        message_ids = []

        # Формируем inline клавиатуру из entities типа inline_keyboard
        reply_markup = None
        if entities:
            keyboard_buttons = []
            for entity in entities:
                if entity.get('type') == 'inline_keyboard':
                    entity_data = entity.get('data', {})
                    buttons = entity_data.get('buttons', [])
                    # Все кнопки из одного entity в одну строку
                    row = []
                    for btn in buttons:
                        text_btn = btn.get('text')
                        url = btn.get('url')
                        style = btn.get('style', None)
                        if text_btn and url:
                            row.append(InlineKeyboardButton(
                                text=text_btn, url=url, style=style))
                    if row:
                        keyboard_buttons.append(row)

            if keyboard_buttons:
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # Если нет медиа - просто текст
        if not media_files:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            message_ids.append(msg.message_id)

        # Одиночный файл
        elif len(media_files) == 1:
            file_info = media_files[0]

            # Нормализуем вход — поддерживаем dict {'data','name','type'} и raw bytes
            if isinstance(file_info, (bytes, bytearray)):
                file_data = bytes(file_info)
                file_name = getattr(file_info, 'name', 'file')
                file_hide = getattr(file_info, 'hide', False)
                file_type = detect_media_type(file_data, file_name)

            elif isinstance(file_info, dict):
                file_data = file_info.get('data')
                file_name = file_info.get('name', 'file')
                file_hide = file_info.get('hide', False)
                file_type = file_info.get('type') or detect_media_type(file_data or b'', file_name)

            else:
                logger.warning(f"Unsupported file_info type for single file: {type(file_info)}")
                raise ValueError("Unsupported media file format")

            if not isinstance(file_data, (bytes, bytearray)):
                logger.error("File data is not bytes for single file")
                raise ValueError("File data is not bytes")

            input_file = BufferedInputFile(file_data, filename=file_name)

            if file_type == 'video':
                msg = await bot.send_video(
                    chat_id=chat_id,
                    video=input_file,
                    caption=text,
                    parse_mode=parse_mode,
                    has_spoiler=file_hide,
                    reply_markup=reply_markup
                )
            else:
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=input_file,
                    caption=text,
                    parse_mode=parse_mode,
                    has_spoiler=file_hide,
                    reply_markup=reply_markup
                )

            message_ids.append(msg.message_id)
        else:
            # Media group (несколько файлов)
            media_group = []

            for idx, file_info in enumerate(media_files):
                # Нормализация формата
                if isinstance(file_info, (bytes, bytearray)):
                    file_data = bytes(file_info)
                    file_name = getattr(file_info, 'name', f'file_{idx}')
                    file_type = detect_media_type(file_data, file_name)
                    file_hide = getattr(file_info, 'hide', False)

                elif isinstance(file_info, dict):
                    file_data = file_info.get('data')
                    file_name = file_info.get('name', f'file_{idx}')
                    file_type = file_info.get('type') or detect_media_type(file_data or b'', file_name)
                    file_hide = file_info.get('hide', False)

                else:
                    logger.warning(f"Unsupported file_info type in media group: {type(file_info)}")
                    continue

                if not isinstance(file_data, (bytes, bytearray)):
                    logger.warning(f"Skipping file {file_name or idx}: data is not bytes")
                    continue

                input_file = BufferedInputFile(file_data, filename=file_name)

                # Caption только для первого элемента
                caption = text if idx == 0 else None
                pm = parse_mode if idx == 0 else None

                if file_type == 'video':
                    media_group.append(InputMediaVideo(
                        media=input_file,
                        caption=caption,
                        parse_mode=pm,
                        has_spoiler=file_hide
                    ))
                else:
                    media_group.append(InputMediaPhoto(
                        media=input_file,
                        caption=caption,
                        parse_mode=pm,
                        has_spoiler=file_hide
                    ))

            # Отправляем media group
            if media_group:
                messages = await bot.send_media_group(
                    chat_id=chat_id,
                    media=media_group
                )
                message_ids = [m.message_id for m in messages]

                # Для media group добавляем клавиатуру отдельным невидимым сообщением
                if reply_markup:
                    keyboard_msg = await bot.send_message(
                        chat_id=chat_id,
                        text="🔗",
                        reply_markup=reply_markup
                    )
                    message_ids.append(keyboard_msg.message_id)
            else:
                logger.warning("No valid media to send in media group")


        for entity in entities or []:
            entity_type = entity.get('type')

            # inline_keyboard уже обработан выше
            if entity_type == 'inline_keyboard':
                continue

            if entity_type == 'poll':
                entity_data = entity.get('data', {})
                res = await send_poll_preview(
                    bot=bot,
                    chat_id=chat_id,
                    entity_data=entity_data
                )
                if isinstance(res.get('message_id'), int):
                    message_ids.append(res.get('message_id'))

        ids_str = ' '.join(map(str, message_ids))
        delete_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🗑 Удалить", 
                callback_data=f"delete_message {ids_str}"
            )]
        ])
        control_msg = await bot.send_message(
            chat_id=chat_id,
            text="👆 Удалить все сообщения превью",
            reply_markup=delete_keyboard
        )
        message_ids.append(control_msg.message_id)

        return {'success': True, 'message_ids': message_ids}
    
    except Exception as e:
        logger.error(f"Ошибка при отправке превью поста: {e}", exc_info=True)
        return {'success': False, 'message_ids': [], 'error': str(e)}


async def prepare_and_send_preview(
    bot: Bot,
    chat_id: int,
    content: str,
    tags: Optional[list[str]] = None,
    client_key: Optional[str] = None,
    post_images: Optional[list[str]] = None,
    cached_files: Optional[dict] = None,
    card_id: Optional[str] = None,
) -> dict:
    """
    Высокоуровневая функция для подготовки и отправки превью.
    Скачивает файлы и отправляет пост.
    
    Args:
        bot: Telegram Bot instance
        chat_id: ID чата для отправки
        content: Сырой контент поста
        tags: Список тегов
        client_key: Ключ клиента для генерации поста
        post_images: Список имён файлов для скачивания
        cached_files: Кэш скачанных файлов (опционально)
    
    Returns:
        {'success': bool, 'message_ids': list[int], 'error': str | None}
    """
    # Генерируем текст поста
    post_text = await generate_post(content, tags, client_key=client_key)

    media_files = []
    if post_images:
        # Скачиваем файлы
        files_to_download = [
            f for f in post_images if not cached_files or f not in cached_files
        ]
        for file_id in files_to_download:
            try:
                cf = await CardFile.get_by_id(_UUID(str(file_id)))
                if not cf:
                    logger.error(f"File record not found: {file_id}")
                    continue

                file_data, status = await _storage_download_file(cf.filename)
                if status == 200 and isinstance(file_data, (bytes, bytearray)):
                    file_name = cf.original_filename or cf.filename
                    media_type = detect_media_type(file_data, file_name)
                    media_files.append({'data': file_data, 'name': file_name, 'type': media_type,
                                        'hide': cf.hide})
                else:
                    logger.error(f"Failed to download file {file_id}: status={status}")
            except Exception as e:
                logger.error(f"Error downloading file {file_id}: {e}", exc_info=True)

        # Собираем все файлы в media_files (cached)
        for f in post_images:
            if cached_files and f in cached_files:
                media_files.append(cached_files[f])

    entities = None
    if card_id and client_key:
        entities_result = await get_entities_for_client(card_id, client_key)
        if entities_result['success'] and entities_result['entities']:
            entities = entities_result['entities']

    # Отправляем
    return await send_post_preview(
        bot=bot,
        chat_id=chat_id,
        text=post_text,
        media_files=media_files,
        entities=entities
    )


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------

async def _send_post_tg(
    executor,
    client_id: str,
    text: str,
    files: list,
    entities: list,
    settings: dict,
) -> dict:
    """Отправка поста через TelegramExecutor."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Строим reply_markup из entities типа inline_keyboard
    reply_markup = None
    keyboard_buttons = []
    for entity in entities:
        if entity.get('type') == 'inline_keyboard':
            row = []
            for btn in entity.get('data', {}).get('buttons', []):
                if btn.get('text') and btn.get('url'):
                    row.append(InlineKeyboardButton(text=btn['text'], url=btn['url']))
            if row:
                keyboard_buttons.append(row)
    if keyboard_buttons:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    chat_id = str(client_id)
    message_ids: list[int] = []
    result: dict = {}

    if not files:
        result = await executor.send_message(
            chat_id=chat_id, text=text, parse_mode='HTML', reply_markup=reply_markup
        )
        if result.get('success'):
            message_ids = [result['message_id']]

    elif len(files) == 1:
        f = files[0]
        if f.get('type') == 'video':
            result = await executor.send_video(
                chat_id=chat_id, video=f['data'], caption=text, parse_mode='HTML',
                has_spoiler=f.get('hide', False), reply_markup=reply_markup
            )
        else:
            result = await executor.send_photo(
                chat_id=chat_id, photo=f['data'], caption=text, parse_mode='HTML',
                has_spoiler=f.get('hide', False), reply_markup=reply_markup
            )
        if result.get('success'):
            message_ids = [result['message_id']]

    else:
        result = await executor.send_media_group(
            chat_id=chat_id, media=files, caption=text, parse_mode='HTML'
        )
        if result.get('success'):
            message_ids = result.get('message_ids', [result.get('message_id')])
            if reply_markup:
                km = await executor.send_message(
                    chat_id=chat_id, text='🔗', reply_markup=reply_markup
                )
                if km.get('success'):
                    message_ids.append(km['message_id'])

    if not result.get('success'):
        return result

    # Опросы и прочие entities
    for entity in entities:
        if entity.get('type') == 'poll':
            from modules.entities_sender import send_poll_preview
            poll_result = await send_poll_preview(
                bot=executor.bot,
                chat_id=int(client_id),
                entity_data=entity.get('data', {})
            )
            if poll_result.get('success') and poll_result.get('message_id'):
                message_ids.append(poll_result['message_id'])

    return {'success': True, 'message_ids': message_ids}


async def _send_post_vk(
    executor,
    text: str,
    files: list,
    settings: dict,
) -> dict:
    """Отправка поста через VKExecutor."""
    import tempfile
    import os

    attachments: list[str] = []
    for f in files:
        file_data = f.get('data')
        file_name = f.get('name', 'file')
        file_type = f.get('type', 'photo')
        if not isinstance(file_data, (bytes, bytearray)):
            continue
        suffix = os.path.splitext(file_name)[1] or ('.mp4' if file_type == 'video' else '.jpg')
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        try:
            if file_type == 'video':
                upload_result = await executor.upload_video_to_wall(tmp_path)
            else:
                upload_result = await executor.upload_photo_to_wall(tmp_path)
            if upload_result.get('success'):
                attachments.append(upload_result['attachment'])
            else:
                logger.warning(f"VK file upload failed: {upload_result.get('error')}")
        finally:
            os.unlink(tmp_path)

    primary_attachments_mode = settings.get('primary_attachments_mode', 'grid')
    return await executor.create_wall_post(
        text=text,
        attachments=attachments or None,
        primary_attachments_mode=primary_attachments_mode
    )


async def send_post(
    card_id: str,
    client_key: str,
    content: str | None = None,
    tags: Optional[list[str]] = None,
    post_images: Optional[list[str]] = None,
    settings: Optional[dict] = None,
    entities: Optional[list] = None,
) -> dict:
    """Универсальная обёртка для немедленной отправки поста через исполнителя.

    Если ``content`` или ``tags`` не переданы, функция самостоятельно подгрузит
    карточку из базы. Текст генерируется через :func:`modules.post_generator.generate_post`,
    файлы скачиваются через :func:`download_files`.
    Отправка производится напрямую через методы нужного executor-а.
    """
    from modules.exec import executor_bridge
    from modules.post_generator import generate_post, render_post_from_card
    from modules.constants import CLIENTS

    if content is None or tags is None:
        from models.Card import Card
        cards = await Card.find(card_id=card_id)
        if cards:
            card = cards[0].to_full_dict()
        else:
            return {"success": False, "error": "Card not found"}
    else:
        card = None

    if card is not None:
        text = await render_post_from_card(card, client_key)
    else:
        text = await generate_post(content or '', tags or [], client_key)

    files = await download_files(post_images or [])

    client_config = CLIENTS.get(client_key)
    if not client_config:
        return {"success": False, "error": f"Client {client_key} not found"}

    executor_name = client_config.get("executor_name") or client_config.get("executor")
    client_id = client_config.get("client_id")

    manager = executor_bridge.get_manager()
    if not manager:
        return {"success": False, "error": "ExecutorManager not initialized"}

    executor = manager.get(executor_name)
    if not executor:
        return {"success": False, "error": f"Executor {executor_name} not found"}

    try:
        from tg.main import TelegramExecutor
        from vk.main import VKExecutor

        if isinstance(executor, TelegramExecutor):
            return await _send_post_tg(
                executor, str(client_id), text, files, entities or [], settings or {}
            )
        elif isinstance(executor, VKExecutor):
            return await _send_post_vk(executor, text, files, settings or {})
        else:
            return {"success": False, "error": f"Unknown executor type: {type(executor)}"}
    except Exception as e:
        logger.error(f"Ошибка при отправке поста: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
