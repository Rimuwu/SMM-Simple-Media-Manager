

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from global_modules.classes.enums import UserRole
from modules.api_client import get_users, update_user
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram import F
from aiogram.filters import Command
from tg.oms import scene_manager
from tg.scenes.create.create_scene import CreateTaskScene
from tg.filters.role_filter import RoleFilter

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
    await message.answer("❌ У вас нет доступа к созданию задач.")


# TEST
@dp.message(Command("update_role"))
async def cmd_update_role(message: Message):
    """Команда для обновления роли пользователя"""
    if not message.from_user:
        return

    new_role = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None

    if not new_role:
        await message.answer("Пожалуйста, укажите новую роль после команды. Например: /update_role admin")
        return

    logger.info(f"User {message.from_user.id} requested role update")

    telegram_id = message.from_user.id
    user_data = await get_users(telegram_id=telegram_id)

    if not user_data:
        await message.answer("Не удалось получить вашу роль пользователя.")
        return
    
    user_data = user_data[0]

    if user_data and 'role' in user_data:
        user_role = user_data['role']

        if new_role not in [role.value for role in UserRole]:
            await message.answer("Неверная роль. Доступные роли: admin, copywriter, editor, customer.")
            return

        await update_user(telegram_id, new_role)
        await message.answer(f"Ваша роль была обновлена с {user_role} на {new_role}.")

        sc = scene_manager.get_scene(telegram_id)
        if sc:
            if sc.data['scene'].get('user_role') == user_role:
                return

            await sc.update_key('scene', 'user_role', user_role)

    else:
        await message.answer("Не удалось получить вашу роль пользователя.")


@dp.message(Command("cancel"))
async def cancel(message: Message):
    print(scene_manager.get_scene(message.from_user.id).__dict__)
    ss = scene_manager.get_scene(message.from_user.id)
    if ss:
        await ss.end()