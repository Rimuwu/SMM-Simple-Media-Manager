

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command
from tg.oms import scene_manager
from tg.scenes.create.create_scene import CreateTaskScene
from tg.filters.role_filter import RoleFilter
from tg.filters.authorize import Authorize

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot


@dp.message(Command("create"), RoleFilter('admin'))
async def cmd_create(message: Message):

    try:
        sc = scene_manager.create_scene(
            message.from_user.id,
            CreateTaskScene,
            bot
        )
        await sc.start()
    except ValueError as e:
        n_s = scene_manager.get_scene(message.from_user.id)
        if n_s:
            await n_s.end()

        sc = scene_manager.create_scene(
            message.from_user.id,
            CreateTaskScene,
            bot
        )
        await sc.start()

@dp.message(Command("create"), RoleFilter('customer'))
async def cmd_create_customer(message: Message):
    await cmd_create(message)

@dp.message(Command("create"))
async def not_authorized_create(message: Message):
    await message.answer("У вас нет прав для использования этой команды.")

@dp.message(Command("cancel"), Authorize())
async def cancel(message: Message):

    ss = scene_manager.get_scene(message.from_user.id)
    if ss:
        await ss.end()
        await message.answer("Вы вышли из текущей сцены.")

@dp.message(Command("cancel"))
async def cancel_na(message: Message):
    await message.answer("У вас нет прав для использования этой команды.")