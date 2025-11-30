from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram.filters import Command
from tg.filters.authorize import Authorize

from tg.oms import scene_manager
from tg.scenes.view.view_tasks_scene import ViewTasksScene

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

@dp.message(Command("tasks"), Authorize())
async def cmd_view_tasks(message: Message):
    """Команда для просмотра задач"""
    if not message.from_user:
        return

    logger.info(f"User {message.from_user.id} requested tasks view")

    try:
        sc = scene_manager.create_scene(
            message.from_user.id,
            ViewTasksScene,
            bot
        )
        await sc.start()
    except ValueError as e:
        # Если сцена уже существует, удаляем и создаем новую
        n_s = scene_manager.get_scene(message.from_user.id)
        if n_s:
            await n_s.end()
        
        scene_manager.remove_scene(message.from_user.id)
        sc = scene_manager.create_scene(
            message.from_user.id,
            ViewTasksScene,
            bot
        )
        await sc.start()

@dp.message(Command("tasks"), Authorize())
async def not_authorized_tasks(message: Message):
    """Команда для просмотра задач"""

    await message.answer("❌ У вас нет доступа к просмотру задач.")