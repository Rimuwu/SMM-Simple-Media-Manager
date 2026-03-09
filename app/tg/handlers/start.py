import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from modules.logs import logger
from modules.exec.executors_manager import manager
from aiogram.filters import Command
from tg.filters.authorize import Authorize
from aiogram.types.bot_command_scope_chat import BotCommandScopeChat
from aiogram.types.bot_command import BotCommand


from tg.oms import scene_manager
from tg.scenes.view.view_tasks_scene import ViewTasksScene
from tg.scenes.edit.task_scene import TaskScene
from models.Card import Card
from models.User import User
from urllib.parse import unquote_plus
import re
from tg.filters.in_dm import InDMorWorkGroup

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

@dp.message(Command("start"), Authorize(), InDMorWorkGroup())
async def start_au(message: Message):
    # Если в команде есть аргументы — пытаемся обработать deep-link открытия задачи
    raw_args = ''
    # aiogram Message.get_args() возвращает аргументы после команды (если поддерживается)
    try:
        raw_args = (message.get_args() or '').strip()
    except Exception:
        raw_args = (message.text or '').strip()
        if ' ' in raw_args:
            raw_args = raw_args.split(' ', 1)[1].strip()

    # URL-декодируем (поддержка deep link t.me/.../?start=...)
    raw_args = unquote_plus(raw_args)

    handled = False

    if raw_args:
        # Попытка найти type-open и id в любой части строки (без зависимости от разделителей)
        action_match = re.search(r"type-open-(view|edit)", raw_args, re.IGNORECASE)
        id_match = re.search(r"id-([A-Za-z0-9\-]+)", raw_args, re.IGNORECASE)

        if action_match and id_match:
            action_raw = action_match.group(1)
            action = action_raw
            task_id = id_match.group(1)

            if action and task_id:
                # Получаем текущего пользователя из БД
                user = await User.by_telegram(message.from_user.id)
                user_role = user.role if user else None
                user_internal_id = str(user.user_id) if user else None

                # Получаем карточку
                cards = [c.to_dict() for c in await Card.find(card_id=task_id)]
                if not cards:
                    await message.answer('❌ Задача не найдена или недоступна.')
                    handled = True
                else:
                    card = cards[0]
                    executor_id = card.get('executor_id')
                    editor_id = card.get('editor_id')
                    customer_id = card.get('customer_id')

                    allowed = False
                    if user_role == 'admin':
                        allowed = True
                    else:
                        # Разрешаем, если пользователь — назначенный копирайтер (executor) или редактор
                        if user_internal_id and str(user_internal_id) == str(executor_id):
                            allowed = True
                        if user_internal_id and str(user_internal_id) == str(editor_id):
                            allowed = True
                        if user_internal_id and str(user_internal_id) == str(customer_id):
                            allowed = True

                    if not allowed:
                        await message.answer('❌ У вас нет доступа к этой задаче.')
                        handled = True
                    else:
                        n_s = scene_manager.get_scene(message.from_user.id)
                        if n_s:
                            await n_s.end()

                        # Открываем просмотр или редактирование
                        if action == 'view':
                            sc = scene_manager.create_scene(message.from_user.id, ViewTasksScene, bot)
                            await sc.update_key('scene', 'selected_task', task_id)
                            sc.page = 'task-detail'

                            await sc.start()
                            handled = True

                        elif action == 'edit':
                            sc = scene_manager.create_scene(message.from_user.id, TaskScene, bot)
                            sc.set_taskid(task_id)
                            await sc.start()
                            handled = True

    if handled:
        return

    # Стандартное приветствие и команды
    text = (
        "👋 Привет! Добро пожаловать в *Cyber-SMM*\n"
        "_Я бот для взаимодействия с отделом SMM, планировщик постов и управления задачами._\n\n"
        "× *(Админ / Заказчик / Копирайтер)*\n"
        "`/create` - Для создания задач. Копирайтер может создать задачу только для себя.\n\n"
        "× *(Админ)*\n"
        "`/users` - Создание и редактирование пользователей.\n"
        "`/design_tasks` - Показать задачи для дизайнеров.\n"
        "`/tags` - Управление хештегами.\n\n"
        "× *(Любая роль)*\n"
        "`/tasks` - Для просмотра заказов, созданных задач или выбора задачи для работы.\n"
        "`/leaderboard` - Лидерборд выполненных задач.\n"
        "`/cancel` - Команда для выхода из текущей сцены.\n"
        "`/help` - Показать справку по использованию бота.\n"
    )

    await message.answer(text, parse_mode="Markdown")
    await bot.set_my_commands(
        [
            BotCommand(command="help", description="Показать справку"),
            BotCommand(command="create", description="Создать новую задачу"),
            BotCommand(command="users", description="Управление пользователями"),
            BotCommand(command="tasks", description="Просмотр задач"),
            BotCommand(command="leaderboard", description="Лидерборд задач"),
            BotCommand(command="cancel", description="Выйти из текущей сцены"),
            BotCommand(command="start", description="Список команд / обновить быстрые команды"),
            BotCommand(command="design_tasks", description="Показать задачи для дизайнеров")
        ],
        BotCommandScopeChat(chat_id=message.chat.id)
    )


@dp.message(Command("start"), InDMorWorkGroup())
async def start(message: Message):
    text = (
        "👋 Привет! Добро пожаловать в *Cyber-SMM*\n"
        "_Я бот для взаимодействия с отделом SMM, планировщик постов и управления задачами._\n\n"
        "❗ Похоже, у вас нет доступа к функционалу бота. Пожалуйста, свяжитесь с @as1aw для получения доступа."
    )

    await message.answer(text, parse_mode="Markdown")