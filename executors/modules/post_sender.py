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
from modules.api_client import brain_api
from global_modules.brain_client import brain_client
from modules.post_generator import generate_post
from modules.logs import executors_logger as logger


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


async def download_kaiten_files(task_id: Union[int, str], file_names: list[str]) -> list[dict]:
    """
    Скачать файлы из Kaiten по именам.
    
    Args:
        task_id: ID карточки в Kaiten
        file_names: Список имён файлов для скачивания
    
    Returns:
        Список словарей: [{'data': bytes, 'name': str, 'type': str}, ...]
    """
    if not task_id or not file_names:
        return []
    
    downloaded_files = []
    
    try:
        # Получаем список файлов карточки
        response = await brain_client.get_kaiten_files(str(task_id))
        
        if not response or not response.get('files'):
            logger.warning(f"No files found for task {task_id}")
            return []
        
        kaiten_files = response['files']
        
        # Ищем файлы по именам и скачиваем (в порядке file_names)
        for file_name in file_names:
            target_file = next(
                (f for f in kaiten_files if f.get('name') == file_name),
                None
            )
            
            if not target_file:
                logger.warning(f"File '{file_name}' not found in task {task_id}")
                continue
            
            file_id = target_file.get('id')
            if not file_id:
                continue
            
            # Скачиваем файл
            file_data, dl_status = await brain_api.get(
                f"/kaiten/files/{file_id}",
                params={"task_id": task_id},
                return_bytes=True
            )
            
            if dl_status == 200 and isinstance(file_data, bytes):
                media_type = detect_media_type(file_data, file_name)
                downloaded_files.append({
                    'data': file_data,
                    'name': file_name,
                    'type': media_type
                })
                logger.info(f"Downloaded file '{file_name}' ({len(file_data)} bytes, type: {media_type})")
            else:
                logger.error(f"Failed to download file '{file_name}'")
    
    except Exception as e:
        logger.error(f"Error downloading files from Kaiten: {e}", exc_info=True)
    
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

        # Если нет медиа - просто текст
        if not media_files:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            message_ids.append(msg.message_id)

        # Одиночный файл
        elif len(media_files) == 1:
            file_info = media_files[0]
            file_data = file_info['data']
            file_name = file_info.get('name', 'file')
            file_type = file_info.get('type', 'photo')
            
            input_file = BufferedInputFile(file_data, filename=file_name)
            
            if file_type == 'video':
                msg = await bot.send_video(
                    chat_id=chat_id,
                    video=input_file,
                    caption=text,
                    parse_mode=parse_mode
                )
            else:
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=input_file,
                    caption=text,
                    parse_mode=parse_mode
                )
            
            message_ids.append(msg.message_id)
        else:
            # Media group (несколько файлов)
            media_group = []
            for idx, file_info in enumerate(media_files):
                file_data = file_info['data']
                file_name = file_info.get('name', f'file_{idx}')
                file_type = file_info.get('type', 'photo')
                
                input_file = BufferedInputFile(file_data, filename=file_name)
                
                # Caption только для первого элемента
                caption = text if idx == 0 else None
                pm = parse_mode if idx == 0 else None
                
                if file_type == 'video':
                    media_group.append(InputMediaVideo(
                        media=input_file,
                        caption=caption,
                        parse_mode=pm
                    ))
                else:
                    media_group.append(InputMediaPhoto(
                        media=input_file,
                        caption=caption,
                        parse_mode=pm
                    ))
            
            # Отправляем media group
            messages = await bot.send_media_group(
                chat_id=chat_id,
                media=media_group
            )
            message_ids = [m.message_id for m in messages]
        
        
        for entity in entities or []:
            entity_type = entity.get('type')

            if entity_type == 'poll':
                entity_data = entity.get('data', {})
                res = await send_poll_preview(
                    bot=bot,
                    chat_id=chat_id,
                    entity_data=entity_data
                )
                print(res)
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
        logger.error(f"Error sending post preview: {e}", exc_info=True)
        return {'success': False, 'message_ids': [], 'error': str(e)}


async def prepare_and_send_preview(
    bot: Bot,
    chat_id: int,
    content: str,
    tags: Optional[list[str]] = None,
    client_key: Optional[str] = None,
    task_id: Optional[Union[int, str]] = None,
    post_images: Optional[list[str]] = None,
    cached_files: Optional[dict] = None,
    card_id: Optional[str] = None,
) -> dict:
    """
    Высокоуровневая функция для подготовки и отправки превью.
    Скачивает файлы из Kaiten и отправляет пост.
    
    Args:
        bot: Telegram Bot instance
        chat_id: ID чата для отправки
        content: Сырой контент поста
        tags: Список тегов
        client_key: Ключ клиента для генерации поста
        task_id: ID задачи в Kaiten
        post_images: Список имён файлов из Kaiten
        cached_files: Кэш скачанных файлов (опционально)
    
    Returns:
        {'success': bool, 'message_ids': list[int], 'error': str | None}
    """
    # Генерируем текст поста
    post_text = generate_post(content, tags, client_key=client_key)
    
    # Скачиваем файлы из Kaiten или берём из кэша
    media_files = []
    if post_images and task_id:
        cache_key = f"{task_id}:{','.join(post_images)}"
        
        if cached_files and cache_key in cached_files:
            media_files = cached_files[cache_key]
        else:
            media_files = await download_kaiten_files(task_id, post_images)
            if cached_files is not None:
                cached_files[cache_key] = media_files
    
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
