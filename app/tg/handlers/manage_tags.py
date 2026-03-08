from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

from modules.exec.executors_manager import manager
from tg.oms.manager import scene_manager
from tg.scenes.tags.tags_scene import TagsScene
from tg.filters.role_filter import RoleFilter
from tg.filters.in_dm import InDMorWorkGroup

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp


@dp.message(Command('tags'), RoleFilter('admin'), InDMorWorkGroup())
async def tags_command(message: Message, bot: Bot):
    """Управление хештегами"""
    try:
        await scene_manager.create_scene(
            message.from_user.id,
            TagsScene,
            bot
        ).start()
    except ValueError:
        n_s = scene_manager.get_scene(message.from_user.id)
        if n_s:
            await n_s.end()

        await scene_manager.create_scene(
            message.from_user.id,
            TagsScene,
            bot
        ).start()


@dp.message(Command('tags'), InDMorWorkGroup())
async def tags_command_nau(message: Message, bot: Bot):
    await message.answer("У вас нет прав для использования этой команды.")
