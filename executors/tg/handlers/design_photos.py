from typing import Optional
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from modules.executors_manager import manager
from modules.api_client import brain_api
from modules.constants import SETTINGS
from modules.logs import executors_logger as logger
from modules.file_utils import download_telegram_file, is_image_by_mime_or_extension
from global_modules.brain_client import brain_client

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


async def upload_image_to_kaiten(card_id: str, file_data: bytes, file_name: str) -> bool:
    """
    Загружает изображение в Kaiten и уведомляет исполнителя.
    Использует общий метод из brain_client.
    """
    try:
        # Загружаем файл через общий метод
        success = await brain_client.upload_file_to_kaiten(
            card_id=card_id,
            file_data=file_data,
            file_name=file_name,
            convert_to_png=True
        )
        
        if success:
            logger.info(f"Файл {file_name} загружен для задачи {card_id}")
            
            # Уведомляем исполнителя через общий метод
            notify_success = await brain_client.notify_executor(
                card_id=card_id,
                message="🖼 К вашей задаче добавлено новое изображение от дизайнеров!"
            )
            
            if notify_success:
                logger.info(f"Уведомление отправлено исполнителю задачи {card_id}")
            else:
                logger.warning(f"Не удалось отправить уведомление для задачи {card_id}")
            
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        return False


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
        
        # Скачиваем через общую функцию
        file_data = await download_telegram_file(bot, photo.file_id)
        if not file_data:
            await message.reply("⚠️ Не удалось скачать файл.", parse_mode="Markdown")
            return

        file_name = f"design_{message.from_user.id}_{message.message_id}.png"
        card_id = card.get('card_id')
        if not card_id:
            await message.reply("⚠️ Ошибка: не найден ID задачи.", parse_mode="Markdown")
            return

        success = await upload_image_to_kaiten(str(card_id), file_data, file_name)

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
    Принимает изображения-документы и конвертирует в PNG.
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

    if not message.document or not message.from_user:
        return
    
    doc = message.document
    mime_type = doc.mime_type or ''
    file_name_orig = doc.file_name or ''
    
    # Проверяем, является ли документ изображением
    is_image = is_image_by_mime_or_extension(mime_type, file_name_orig)
    
    if not is_image:
        # Отправляем сообщение что нужно фото
        await message.reply(
            "⚠️ Пожалуйста, отправьте изображение как **фото**, а не как файл/документ.\n\n"
            "💡 Чтобы отправить как фото:\n"
            "1. Выберите изображение\n"
            "2. Убедитесь что опция «Сжать изображение» включена\n"
            "3. Не отправляйте как «Файл»",
            parse_mode="Markdown"
        )
        return
    
    # Это изображение-документ - обрабатываем
    logger.info(f"Получено изображение-документ для задачи {card['card_id']} от {message.from_user.id}")
    
    try:
        # Скачиваем через общую функцию
        file_data = await download_telegram_file(bot, doc.file_id)
        if not file_data:
            await message.reply("⚠️ Не удалось скачать файл.", parse_mode="Markdown")
            return

        base_name = f"design_{message.from_user.id}_{message.message_id}"
        file_name = f"{base_name}.png"

        card_id = card.get('card_id')
        if not card_id:
            await message.reply("⚠️ Ошибка: не найден ID задачи.", parse_mode="Markdown")
            return

        success = await upload_image_to_kaiten(str(card_id), file_data, file_name)

        if success:
            await message.reply("✅ Изображение добавлено к задаче!", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Не удалось загрузить изображение.", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка обработки документа-изображения: {e}")
        await message.reply(f"⚠️ Ошибка: {str(e)[:100]}", parse_mode="Markdown")
