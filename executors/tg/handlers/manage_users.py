

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command

from tg.oms.manager import scene_manager
from tg.scenes.admin.users_scene import UsersScene
from tg.filters.role_filter import RoleFilter

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

@dp.message(Command('users'), RoleFilter('admin'))
async def users_command(message: Message, bot: Bot):
    """Управление пользователями"""
    try:
        await scene_manager.create_scene(
            message.from_user.id,
            UsersScene,
            bot
        ).start()
    except ValueError:
        # Если сцена уже существует, удаляем её и создаем новую
        scene_manager.remove_scene(message.from_user.id)
        await scene_manager.create_scene(
            message.from_user.id,
            UsersScene,
            bot
        ).start()
        
@dp.message(Command('users'))
async def users_command(message: Message, bot: Bot):
    """Управление пользователями"""
    await message.answer("У вас нет прав для использования этой команды.")