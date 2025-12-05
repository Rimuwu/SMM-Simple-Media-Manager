"""
Обработчик ответов на сообщения дизайнерам с фотографиями и документами
"""
import io
from typing import Optional
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from PIL import Image
from modules.executors_manager import manager
from modules.api_client import brain_api
from modules.constants import SETTINGS
from modules.logs import executors_logger as logger

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp  # type: ignore
bot: Bot = client_executor.bot  # type: ignore


async def find_card_by_reply(reply_message_id: int) -> Optional[dict]:
    """Ищет карточку по ID сообщения, на которое ответили"""
    try:
        response, status = await brain_api.get('/card/get', params={})
        if status != 200:
            return None
        
        for c in response:
            if isinstance(c, dict) and c.get('prompt_message') == reply_message_id:
                return c
        return None
    except Exception as e:
        logger.error(f"Ошибка поиска карточки: {e}")
        return None


async def upload_image_to_kaiten(card_id: str, file_data: bytes, file_name: str):
    """Загружает изображение в Kaiten и уведомляет исполнителя"""
    try:
        form_data = aiohttp.FormData()
        form_data.add_field('card_id', str(card_id))
        form_data.add_field(
            'file',
            file_data,
            filename=file_name,
            content_type='image/jpeg'
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://brain:8000/kaiten/upload-file',
                data=form_data
            ) as resp:
                if resp.status == 200:
                    logger.info(f"Файл {file_name} загружен для задачи {card_id}")
                    
                    # Уведомляем исполнителя
                    try:
                        notify_data = {
                            "card_id": str(card_id),
                            "message": "🖼 К вашей задаче добавлено новое изображение от дизайнеров!"
                        }
                        async with session.post(
                            'http://brain:8000/card/notify-executor',
                            json=notify_data
                        ) as notify_resp:
                            if notify_resp.status == 200:
                                logger.info(f"Уведомление отправлено исполнителю задачи {card_id}")
                    except Exception as notify_err:
                        logger.error(f"Ошибка отправки уведомления: {notify_err}")
                    
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка загрузки файла: {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        return False


def convert_to_jpeg(file_data: bytes) -> bytes:
    """Конвертирует изображение в JPEG"""
    try:
        image = Image.open(io.BytesIO(file_data))
        # Конвертируем в RGB если нужно (для PNG с прозрачностью)
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
        return output.getvalue()
    except Exception as e:
        logger.error(f"Ошибка конвертации изображения: {e}")
        raise


@dp.message(F.photo, F.reply_to_message)
async def handle_design_photo_reply(message: Message):
    """
    Обработчик фото-ответов на сообщения с ТЗ дизайнерам.
    """
    design_group = SETTINGS.get('design_group')
    
    if message.chat.id != design_group:
        return
    
    if not message.reply_to_message:
        return
        
    reply_message_id = message.reply_to_message.message_id
    card = await find_card_by_reply(reply_message_id)
    
    if not card:
        return
    
    if not message.photo or not message.from_user:
        return
    
    logger.info(f"Получено фото для задачи {card['card_id']} от {message.from_user.id}")
    
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        if not file.file_path:
            await message.reply("⚠️ Не удалось получить файл.", parse_mode="Markdown")
            return
            
        file_data = await bot.download_file(file.file_path)
        if not file_data:
            await message.reply("⚠️ Не удалось скачать файл.", parse_mode="Markdown")
            return
        
        file_name = f"design_{message.from_user.id}_{message.message_id}.jpg"
        card_id = card.get('card_id')
        if not card_id:
            await message.reply("⚠️ Ошибка: не найден ID задачи.", parse_mode="Markdown")
            return
        
        success = await upload_image_to_kaiten(str(card_id), file_data.read(), file_name)
        
        if success:
            await message.reply("✅ Фото добавлено к задаче!", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Не удалось загрузить фото.", parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Ошибка обработки фото-ответа: {e}")
        await message.reply(f"⚠️ Ошибка: {str(e)[:100]}", parse_mode="Markdown")


@dp.message(F.document, F.reply_to_message)
async def handle_design_document_reply(message: Message):
    """
    Обработчик документов от дизайнеров.
    Отклоняет документы и просит отправить фото.
    """
    design_group = SETTINGS.get('design_group')
    
    if message.chat.id != design_group:
        return
    
    if not message.reply_to_message:
        return
        
    reply_message_id = message.reply_to_message.message_id
    card = await find_card_by_reply(reply_message_id)
    
    if not card:
        return
    
    # Отправляем сообщение что нужно фото
    await message.reply(
        "⚠️ Пожалуйста, отправьте изображение как **фото**, а не как файл/документ.\n\n"
        "💡 Чтобы отправить как фото:\n"
        "1. Выберите изображение\n"
        "2. Убедитесь что опция «Сжать изображение» включена\n"
        "3. Не отправляйте как «Файл»",
        parse_mode="Markdown"
    )
