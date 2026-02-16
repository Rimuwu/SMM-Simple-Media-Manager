from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.executors_manager import manager
from aiogram.filters import Command

from tg.oms.manager import scene_manager
from tg.scenes.admin.users_scene import UsersScene
from tg.filters.role_filter import RoleFilter
from tg.filters.in_dm import InDMorWorkGroup

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp

@dp.message(Command('users'), RoleFilter('admin'), InDMorWorkGroup())
async def users_command(message: Message, bot: Bot):
    """Управление пользователями"""
    try:
        await scene_manager.create_scene(
            message.from_user.id,
            UsersScene,
            bot
        ).start()
    except ValueError:
        n_s = scene_manager.get_scene(message.from_user.id)
        if n_s:
            await n_s.end()

        await scene_manager.create_scene(
            message.from_user.id,
            UsersScene,
            bot
        ).start()

@dp.message(Command('users'), InDMorWorkGroup())
async def users_command_nau(message: Message, bot: Bot):
    """Управление пользователями"""
    await message.answer("У вас нет прав для использования этой команды.")