import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from modules.logs import logger
from modules.executors_manager import manager
from aiogram.filters import Command
from tg.filters.authorize import Authorize
from aiogram.types.bot_command_scope_chat import BotCommandScopeChat
from aiogram.types.bot_command import BotCommand
from tg.filters.in_dm import InDMorWorkGroup

from tg.oms import scene_manager
from tg.scenes.view.view_tasks_scene import ViewTasksScene
from tg.scenes.edit.task_scene import TaskScene
from global_modules.brain_client import brain_client
from urllib.parse import unquote_plus
import re

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot

# Help texts for different roles (moved to module scope for reuse)
HELP_TEXTS = {
    'copywriter': (
        "✍️ *Помощь для копирайтера*\n\n"
        "• *Создание задачи*: команда `/create` — заполните поля задачи и создайте задачу для себя.\n"
        "• *Просмотр задач*: `/tasks` — выберите задачу, откройте и настройте: контент, теги, картинки.\n"
        "• После настройки отправьте задачу на проверку (кнопка «Отправить на проверку»).\n"
        "• *Где брать задачи на проверку*: на форуме задач (раздел «Форум задач»)."
    ),
    'customer': (
        "👤 *Помощь для заказчика*\n\n"
        "• *Создание задачи*: команда `/create` — опишите задачу и требования.\n"
        "• *Просмотр задач*: `/tasks` — в карточке можно оставлять комментарии исполнителю и прикреплять файлы.\n"
        "• *Просмотр итогового вида*: в карточке доступен финальный вариант работы. Вы получите уведомление о готовности.\n"
    ),
    'editor': (
        "🖋 *Помощь для редактора*\n\n"
        "• Редактор может просматривать помощь копирайтера и дополнительную информацию для проверки.\n"
        "• *Просмотр задач*: `/tasks` — используйте фильтр «Проверяемые», чтобы отобрать задачи на проверку.\n"
        "• Откройте задачу и оставьте комментарии исполнителю или верните на доработку при необходимости.\n"
        "• Задачи на проверку также берутся с форума задач."
    ),
    'admin': (
        "🛠️ *Помощь для администратора*\n\n"
        "У администратора нет отдельной инструкции — он может просмотреть помощь для всех ролей.\n"
        "Используйте кнопку «Все» чтобы увидеть помощь для других ролей."
    )
}


@dp.message(Command("help"), Authorize(), InDMorWorkGroup())
async def help(message: Message):
    """Show help using inline buttons only. No role argument accepted."""
    try:
        user_role = await brain_client.get_user_role(message.from_user.id)

        # Copywriter and Customer get direct help text (no buttons)
        if user_role == 'copywriter':
            await message.answer(HELP_TEXTS['copywriter'], parse_mode='Markdown')
            return

        if user_role == 'customer':
            await message.answer(HELP_TEXTS['customer'], parse_mode='Markdown')
            return

        # Editor sees own help and a button to view copywriter help
        if user_role == 'editor':
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='✍️ Про копирайтера', callback_data='help:copywriter')],
                [InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')]
            ])
            await message.answer(HELP_TEXTS['editor'], reply_markup=kb, parse_mode='Markdown')
            return

        # Admin (or unknown role) sees full menu
        role_name = user_role or 'не определена'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✍️ Копирайтер', callback_data='help:copywriter'), InlineKeyboardButton(text='🧑‍⚖️ Редактор', callback_data='help:editor')],
            [InlineKeyboardButton(text='👤 Заказчик', callback_data='help:customer'), InlineKeyboardButton(text='🛠️ Админ', callback_data='help:admin')],
            [InlineKeyboardButton(text='📚 Все', callback_data='help:all'), InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')]
        ])
        await message.answer(f"Выберите тип помощи. Ваша роль: *{role_name}*", reply_markup=kb, parse_mode='Markdown')

    except Exception:
        logger.exception("Error in help handler")
        await message.answer("Произошла ошибка при формировании справки. Попробуйте позже.",
                parse_mode='Markdown')


@dp.callback_query(Authorize(), InDMorWorkGroup(), lambda call: (call.data or '').lower().startswith('help:'))
async def help_callback(call: CallbackQuery):
    """Handle inline help button presses with role-specific buttons."""
    try:
        data = (call.data or '').lower()
        if not data.startswith('help:'):
            return

        if not call.message:
            await call.answer()
            return

        action = data.split(':', 1)[1]
        viewer_role = await brain_client.get_user_role(call.from_user.id)

        if action == 'close':
            try:
                await call.message.delete()
            except Exception:
                pass
            await call.answer()
            return

        if action == 'all':
            # only admin can view consolidated help
            if viewer_role != 'admin':
                await call.answer('Недостаточно прав')
                return
            parts = [HELP_TEXTS[k] for k in ('copywriter', 'editor', 'customer')]
            parts.append(HELP_TEXTS['admin'])
            await call.message.edit_text("\n\n".join(parts),
                parse_mode='Markdown')
            await call.answer()
            return

        if action in HELP_TEXTS:
            buttons = []
            if action == 'editor':
                # editor page should include a button to view copywriter help
                buttons.append([InlineKeyboardButton(text='✍️ Про копирайтера', callback_data='help:copywriter')])
                if viewer_role == 'admin':
                    buttons.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='help:menu'), InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')])
                else:
                    buttons.append([InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')])
            else:
                # copywriter/customer/admin views: admin gets navigation buttons, others get close
                if viewer_role == 'admin':
                    buttons.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='help:menu'), InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')])
                else:
                    # for copywriter/customer viewers we keep it buttonless, but include close to allow dismissing
                    if action in ('copywriter', 'customer'):
                        buttons = []
                    else:
                        buttons.append([InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')])

            kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
            if kb:
                await call.message.edit_text(HELP_TEXTS[action], reply_markup=kb,
                parse_mode='Markdown')
            else:
                await call.message.edit_text(HELP_TEXTS[action],
                parse_mode='Markdown')
            await call.answer()
            return

        if action == 'menu':
            viewer_role = await brain_client.get_user_role(call.from_user.id)
            if viewer_role == 'copywriter':
                await call.message.edit_text(HELP_TEXTS['copywriter'],
                parse_mode='Markdown')
                await call.answer()
                return
            if viewer_role == 'customer':
                await call.message.edit_text(HELP_TEXTS['customer'],
                parse_mode='Markdown')
                await call.answer()
                return
            if viewer_role == 'editor':
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='✍️ Про копирайтера', callback_data='help:copywriter')],
                    [InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')]
                ])
                await call.message.edit_text(HELP_TEXTS['editor'], reply_markup=kb,
                parse_mode='Markdown')
                await call.answer()
                return
            # admin or unknown -> full menu
            role_name = viewer_role or 'не определена'
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='✍️ Копирайтер', callback_data='help:copywriter'), InlineKeyboardButton(text='🧑‍⚖️ Редактор', callback_data='help:editor')],
                [InlineKeyboardButton(text='👤 Заказчик', callback_data='help:customer'), InlineKeyboardButton(text='🛠️ Админ', callback_data='help:admin')],
                [InlineKeyboardButton(text='📚 Все', callback_data='help:all'), InlineKeyboardButton(text='❌ Закрыть', callback_data='help:close')]
            ])
            await call.message.edit_text(
                f"Выберите тип помощи. Ваша роль: *{role_name}*", reply_markup=kb,
                parse_mode='Markdown'
                )
            await call.answer()
            return

        await call.answer()

    except Exception:
        logger.exception('Error in help callback')
        try:
            await call.answer('Произошла ошибка при обработке запроса')
        except Exception:
            pass