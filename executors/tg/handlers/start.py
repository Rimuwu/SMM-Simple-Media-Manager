from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from aiogram.filters import Command
from tg.filters.authorize import Authorize
from aiogram.types.bot_command_scope_chat import BotCommandScopeChat
from aiogram.types.bot_command import BotCommand


from tg.oms import scene_manager
from tg.scenes.view.view_tasks_scene import ViewTasksScene

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

@dp.message(Command("start"), Authorize())
async def start_au(message: Message):
    
    text = (
        "👋 Привет! Добро пожаловать в *SMM Simple Media Manager*\n"
        "_Я бот для взаимодействия с отделом SMM, планировщик постов и управления задачами._\n\n"
        "× *(Админ / Заказчик)*\n"
        "/create - Для создания задач.\n\n"
        "× *(Админ)*\n"
        "/users - Создание и редактирование пользователей.\n\n"
        "× *(Любая роль)*\n"
        "/tasks - Для просмотра заказов, созданных задач или выбора задачи для работы.\n"
        "/leaderboard - Лидерборд выполненных задач.\n"
        "/cancel - Команда для выхода из текущей сцены."
    )

    await message.answer(text, parse_mode="Markdown")
    await bot.set_my_commands(
        [
            BotCommand(command="create", description="Создать новую задачу"),
            BotCommand(command="users", description="Управление пользователями"),
            BotCommand(command="tasks", description="Просмотр задач"),
            BotCommand(command="leaderboard", description="Лидерборд задач"),
            BotCommand(command="cancel", description="Выйти из текущей сцены"),
            BotCommand(command="start", description="Список команд / обновить быстрые команды"),
        ],
        BotCommandScopeChat(chat_id=message.chat.id)
    )


@dp.message(Command("start"))
async def start(message: Message):

    text = (
        "👋 Привет! Добро пожаловать в SMM Simple Media Manager Bot.\n"
        "_Я бот для взаимодействия с отделом SMM, планировщик постов и управления задачами._\n\n"
        "❗ Похоже, у вас нет доступа к функционалу бота. Пожалуйста, свяжитесь с @as1aw для получения доступа."
    )

    await message.answer(text, parse_mode="Markdown")
