"""
Модуль для работы с файлами: скачивание, конвертация, определение типов.
Используется в Telegram боте и VK executor.
"""
import io
from typing import Optional, Tuple, Set, BinaryIO
from PIL import Image


# Поддерживаемые типы файлов
IMAGE_MIMES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v']
VIDEO_MIMES = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm']


def detect_file_type_by_bytes(data: bytes) -> Tuple[str, str, str]:
    """
    Определяет тип файла по первым байтам (magic bytes).
    
    Returns:
        Tuple[mime_type, extension, file_type]: ('image/png', '.png', 'photo')
    """
    if len(data) < 12:
        return 'application/octet-stream', '', 'document'
    
    # PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png', '.png', 'photo'
    
    # JPEG
    if data[:2] == b'\xff\xd8':
        return 'image/jpeg', '.jpg', 'photo'
    
    # GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif', '.gif', 'photo'
    
    # WebP
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp', '.webp', 'photo'
    
    # BMP
    if data[:2] == b'BM':
        return 'image/bmp', '.bmp', 'photo'
    
    # TIFF (little-endian and big-endian)
    if data[:4] in (b'II\x2a\x00', b'MM\x00\x2a'):
        return 'image/tiff', '.tiff', 'photo'
    
    # MP4 / MOV (ftyp box)
    if data[4:8] == b'ftyp':
        ftyp_brand = data[8:12]
        if ftyp_brand in (b'mp41', b'mp42', b'isom', b'avc1', b'M4V ', b'M4A '):
            return 'video/mp4', '.mp4', 'video'
        elif ftyp_brand in (b'qt  ', b'moov'):
            return 'video/quicktime', '.mov', 'video'
        return 'video/mp4', '.mp4', 'video'
    
    # WebM / MKV (EBML header)
    if data[:4] == b'\x1a\x45\xdf\xa3':
        # Check for WebM doctype
        if b'webm' in data[:64].lower():
            return 'video/webm', '.webm', 'video'
        return 'video/x-matroska', '.mkv', 'video'
    
    # AVI (RIFF header with AVI)
    if data[:4] == b'RIFF' and data[8:12] == b'AVI ':
        return 'video/avi', '.avi', 'video'
    
    # JPEG 2000
    if data[:4] == b'\x00\x00\x00\x0c' and data[4:8] == b'jP  ':
        return 'image/jp2', '.jp2', 'photo'
    
    # По умолчанию - неизвестный файл
    return 'application/octet-stream', '', 'document'


def is_image_by_mime_or_extension(mime_type: Optional[str], filename: Optional[str]) -> bool:
    """
    Проверяет, является ли файл изображением по MIME-типу или расширению.
    """
    if mime_type and mime_type in IMAGE_MIMES:
        return True
    
    if filename:
        filename_lower = filename.lower()
        if any(filename_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
            return True
    
    return False


def is_video_by_mime_or_extension(mime_type: Optional[str], filename: Optional[str]) -> bool:
    """
    Проверяет, является ли файл видео по MIME-типу или расширению.
    """
    if mime_type and mime_type in VIDEO_MIMES:
        return True
    
    if filename:
        filename_lower = filename.lower()
        if any(filename_lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
            return True
    
    return False


def convert_image_to_png(file_data: bytes) -> bytes:
    """
    Конвертирует изображение в PNG формат.
    Поддерживает RGBA, прозрачность сохраняется.
    
    Args:
        file_data: Бинарные данные исходного изображения
        
    Returns:
        bytes: PNG данные изображения
    """
    image = Image.open(io.BytesIO(file_data))
    
    # Конвертируем в RGBA для поддержки прозрачности
    if image.mode not in ('RGBA', 'RGB'):
        if image.mode == 'P':
            # Палитровый режим может иметь прозрачность
            image = image.convert('RGBA')
        elif image.mode in ('LA', 'L'):
            # Grayscale с альфа-каналом или без
            image = image.convert('RGBA')
        else:
            image = image.convert('RGBA')
    
    output = io.BytesIO()
    image.save(output, format='PNG', optimize=True)
    return output.getvalue()


def convert_image_to_jpeg(file_data: bytes, quality: int = 95) -> bytes:
    """
    Конвертирует изображение в JPEG формат.
    Прозрачность заменяется белым фоном.
    
    Args:
        file_data: Бинарные данные исходного изображения
        quality: Качество JPEG (1-100)
        
    Returns:
        bytes: JPEG данные изображения
    """
    image = Image.open(io.BytesIO(file_data))
    
    # Конвертируем в RGB (JPEG не поддерживает прозрачность)
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        if image.mode in ('RGBA', 'LA'):
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=quality)
    return output.getvalue()


def generate_unique_filename(
    original_name: str, 
    existing_names: Set[str],
    default_name: str = 'file'
) -> str:
    """
    Генерирует уникальное имя файла.
    
    Args:
        original_name: Исходное имя файла
        existing_names: Множество уже существующих имён
        default_name: Имя по умолчанию, если original_name пустое
        
    Returns:
        str: Уникальное имя файла
    """
    if not original_name:
        original_name = default_name
    
    # Если имя уже уникально - возвращаем как есть
    if original_name not in existing_names:
        return original_name
    
    # Разделяем имя и расширение
    if '.' in original_name:
        name_part, ext = original_name.rsplit('.', 1)
        ext = '.' + ext
    else:
        name_part = original_name
        ext = ''
    
    # Ищем уникальный номер
    counter = 1
    while True:
        new_name = f"{name_part}_{counter}{ext}"
        if new_name not in existing_names:
            return new_name
        counter += 1


def get_filename_with_extension(
    original_name: Optional[str],
    file_data: bytes,
    preferred_format: str = 'png'
) -> str:
    """
    Возвращает имя файла с правильным расширением на основе содержимого.
    
    Args:
        original_name: Исходное имя файла (может быть None)
        file_data: Бинарные данные файла
        preferred_format: Предпочитаемый формат для изображений ('png' или 'jpg')
        
    Returns:
        str: Имя файла с расширением
    """
    mime_type, extension, file_type = detect_file_type_by_bytes(file_data)
    
    if original_name:
        # Имя есть - проверяем расширение
        if '.' in original_name:
            name_part, ext = original_name.rsplit('.', 1)
            # Если расширение соответствует типу - оставляем
            if f'.{ext.lower()}' == extension.lower():
                return original_name
            # Для изображений можем заменить на предпочитаемый формат
            if file_type == 'photo':
                if preferred_format == 'png':
                    return f"{name_part}.png"
                elif preferred_format == 'jpg':
                    return f"{name_part}.jpg"
            return original_name
        else:
            # Нет расширения - добавляем
            if extension:
                return f"{original_name}{extension}"
            return original_name
    else:
        # Имени нет - генерируем
        if file_type == 'photo':
            return f"photo.{preferred_format}"
        elif file_type == 'video':
            return f"video{extension}"
        else:
            return f"file{extension}" if extension else "file"


def extract_file_info_from_telegram_message(message) -> Optional[dict]:
    """
    Извлекает информацию о файле из сообщения Telegram.
    
    Args:
        message: Объект Message из aiogram
        
    Returns:
        dict с ключами: file_id, file_unique_id, file_name, file_size, mime_type, file_type
        или None если файл не найден
    """
    if message.photo:
        # Берём самую большую версию фото
        photo = message.photo[-1]
        return {
            'file_id': photo.file_id,
            'file_unique_id': photo.file_unique_id,
            'file_name': None,  # Фото не имеют имени
            'file_size': photo.file_size,
            'mime_type': 'image/jpeg',  # Telegram хранит фото как JPEG
            'file_type': 'photo'
        }
    
    elif message.document:
        doc = message.document
        return {
            'file_id': doc.file_id,
            'file_unique_id': doc.file_unique_id,
            'file_name': doc.file_name,
            'file_size': doc.file_size,
            'mime_type': doc.mime_type,
            'file_type': 'document'
        }
    
    elif message.video:
        video = message.video
        return {
            'file_id': video.file_id,
            'file_unique_id': video.file_unique_id,
            'file_name': video.file_name,
            'file_size': video.file_size,
            'mime_type': video.mime_type or 'video/mp4',
            'file_type': 'video'
        }
    
    elif message.animation:
        anim = message.animation
        return {
            'file_id': anim.file_id,
            'file_unique_id': anim.file_unique_id,
            'file_name': anim.file_name,
            'file_size': anim.file_size,
            'mime_type': anim.mime_type or 'video/mp4',
            'file_type': 'animation'
        }
    
    elif message.audio:
        audio = message.audio
        return {
            'file_id': audio.file_id,
            'file_unique_id': audio.file_unique_id,
            'file_name': audio.file_name,
            'file_size': audio.file_size,
            'mime_type': audio.mime_type or 'audio/mpeg',
            'file_type': 'audio'
        }
    
    elif message.voice:
        voice = message.voice
        return {
            'file_id': voice.file_id,
            'file_unique_id': voice.file_unique_id,
            'file_name': None,
            'file_size': voice.file_size,
            'mime_type': voice.mime_type or 'audio/ogg',
            'file_type': 'voice'
        }
    
    elif message.video_note:
        vnote = message.video_note
        return {
            'file_id': vnote.file_id,
            'file_unique_id': vnote.file_unique_id,
            'file_name': None,
            'file_size': vnote.file_size,
            'mime_type': 'video/mp4',
            'file_type': 'video_note'
        }
    
    return None


async def download_telegram_file(bot, file_id: str) -> Optional[bytes]:
    """
    Скачивает файл из Telegram по file_id.
    
    Args:
        bot: Объект Bot из aiogram
        file_id: ID файла в Telegram
        
    Returns:
        bytes: Бинарные данные файла или None при ошибке
    """
    try:
        file = await bot.get_file(file_id)
        if not file.file_path:
            return None
        
        file_data = await bot.download_file(file.file_path)
        if not file_data:
            return None
        
        return file_data.read()
    except Exception:
        return None


def process_image_for_storage(
    file_data: bytes,
    original_name: Optional[str] = None,
    convert_to_png: bool = True
) -> Tuple[bytes, str, str]:
    """
    Обрабатывает изображение для хранения.
    
    Args:
        file_data: Исходные данные файла
        original_name: Исходное имя файла
        convert_to_png: Конвертировать в PNG
        
    Returns:
        Tuple[processed_data, filename, mime_type]
    """
    mime_type, extension, file_type = detect_file_type_by_bytes(file_data)
    
    if file_type != 'photo':
        # Не изображение - возвращаем как есть
        filename = original_name or f"file{extension}"
        return file_data, filename, mime_type
    
    if convert_to_png:
        processed_data = convert_image_to_png(file_data)
        if original_name:
            if '.' in original_name:
                name_part = original_name.rsplit('.', 1)[0]
            else:
                name_part = original_name
            filename = f"{name_part}.png"
        else:
            filename = "photo.png"
        return processed_data, filename, 'image/png'
    else:
        # Оставляем в исходном формате
        filename = get_filename_with_extension(original_name, file_data, 'png')
        return file_data, filename, mime_type
