from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from global_modules import brain_client
from global_modules.classes.enums import CardStatus
from modules.text_generators import card_executed, forum_message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command

from modules.api_client import brain_api as api
from modules.api_client import get_user_role, get_cards
from modules.api_client import update_card, get_users
from tg.oms.manager import scene_manager

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

@dp.callback_query(F.data == "take_task")
async def take_task(callback: CallbackQuery):
    logger.info(f"Пользователь {callback.from_user.id} нажал 'Забрать задание'")

    message_id = callback.message.message_id
    users = await get_users(telegram_id=callback.from_user.id)
    user = users[0] if users else None

    if not user:
        await callback.answer(
            "Вы не зарегистрированы в системе.", show_alert=True)
        return

    card = await brain_client.get_card_by_message_id(message_id)

    if not card:
        await callback.answer(
            "Задание не найдено или уже взято другим исполнителем.", show_alert=True)
        await bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
        return

    card_id = card['card_id']

    if not card:
        await callback.answer(
            "Задание не найдено.", show_alert=True)
        return 
    
    if card['executor_id'] is not None:
        await callback.answer(
            "Задание уже взято другим исполнителем.", show_alert=True)
        return

    data = await card_executed(
        card_id=card_id,
        telegram_id=callback.from_user.id
    )

    if not data.get("success", False):
        await callback.answer(
            "Не удалось взять задание в работу.", show_alert=True)
        return
    
    # Сообщение на форуме обновится автоматически из card.py при смене статуса на edited
    logger.info(f"Пользователь {callback.from_user.id} взял задание {card_id}")

    await callback.answer(
        "Вы успешно взяли задание в работу.", show_alert=True)
    
    # Открываем сцену редактирования задачи
    try:
        from tg.scenes.edit.task_scene import TaskScene

        # Закрываем существующую сцену если есть
        if not scene_manager.has_scene(callback.from_user.id):

            # Создаём новую сцену
            task_scene: TaskScene = scene_manager.create_scene(
                callback.from_user.id, 
                TaskScene, 
                bot
            )
            task_scene.set_taskid(card_id)
            await task_scene.start()

        logger.info(f"Сцена user-task открыта для пользователя {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка открытия сцены user-task: {e}")


@dp.callback_query(F.data == "edit_task")
async def edit_task(callback: CallbackQuery):
    """Взять задание на проверку (назначить себя редактором)"""
    logger.info(f"Пользователь {callback.from_user.id} нажал 'Взять в проверку'")

    message_id = callback.message.message_id
    users = await get_users(telegram_id=callback.from_user.id)
    user = users[0] if users else None

    if not user:
        await callback.answer(
            "Вы не зарегистрированы в системе.", show_alert=True)
        return

    # Проверяем что пользователь - редактор или админ
    user_role = user.get('role')
    if user_role not in ['editor', 'admin']:
        await callback.answer(
            "Только редакторы и админы могут взять задание на проверку.", show_alert=True)
        return

    card = await brain_client.get_card_by_message_id(message_id)

    if not card:
        await callback.answer(
            "Задание не найдено или уже на проверке.", show_alert=True)
        await bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
        return

    card_id = card['card_id']

    if not card:
        await callback.answer(
            "Задание не найдено.", show_alert=True)
        return 

    # Проверяем что задание на проверке и редактор не назначен
    if card['status'] != CardStatus.review.value:
        await callback.answer(
            "Задание не на проверке.", show_alert=True)
        return

    if card['editor_id'] is not None:
        await callback.answer(
            "Задание уже взято другим редактором.", show_alert=True)
        return

    # Назначаем редактора
    editor_id = str(user['user_id'])
    result = await update_card(
        card_id=card_id,
        editor_id=editor_id
    )

    if not result:
        await callback.answer(
            "Не удалось взять задание на проверку.", show_alert=True)
        return
    
    logger.info(f"Пользователь {callback.from_user.id} взял задание {card_id} на проверку")

    await callback.answer(
        "Вы успешно взяли задание на проверку.", show_alert=True)
    
    # Открываем сцену редактирования задачи
    try:
        from tg.scenes.edit.task_scene import TaskScene
        
        # Закрываем существующую сцену если есть
        if scene_manager.has_scene(callback.from_user.id):
            old_scene = scene_manager.get_scene(callback.from_user.id)
            if old_scene:
                await old_scene.end()
        
        # Создаём новую сцену
        task_scene: TaskScene = scene_manager.create_scene(
            callback.from_user.id, 
            TaskScene, 
            bot
        )
        task_scene.set_taskid(card_id)
        await task_scene.start()

        logger.info(f"Сцена user-task открыта для редактора {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка открытия сцены user-task: {e}")