

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command
from datetime import datetime, timedelta

from global_modules.api_client import APIClient
from tg.oms import scene_manager
from tg.scenes.edit.task_scene import TaskScene
from tg.scenes.create.create_scene import CreateTaskScene

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

@dp.message(Command("test"))
async def cmd_test(message: Message):
    print("TEST")

    try:
        sc = scene_manager.create_scene(
            message.from_user.id,
            TaskScene,
            bot
        )
        await sc.start()
    except ValueError as e:
        scene_manager.remove_scene(message.from_user.id)
        sc = scene_manager.create_scene(
            message.from_user.id,
            TaskScene,
            bot
        )
        await sc.start()

@dp.message(Command("create"))
async def cmd_create(message: Message):
    print("TEST")

    try:
        sc = scene_manager.create_scene(
            message.from_user.id,
            CreateTaskScene,
            bot
        )
        await sc.start()
    except ValueError as e:
        scene_manager.remove_scene(message.from_user.id)
        sc = scene_manager.create_scene(
            message.from_user.id,
            CreateTaskScene,
            bot
        )
        await sc.start()