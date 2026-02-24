from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from modules.executors_manager import manager
from modules.constants import SETTINGS
from global_modules.brain_client import brain_client
from modules.logs import executors_logger as logger

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp  # type: ignore
bot: Bot = client_executor.bot  # type: ignore

# идентификатор чата группы дизайнеров
DESIGN_GROUP: int = SETTINGS.get('design_group')

TASKS_PER_PAGE = 5


def _make_message_link(chat_id: int, message_id: int) -> str:
    """Составляет ссылку на сообщение в супергруппе.

    Для внутренних ссылок используется формат
    `https://t.me/c/<chat_id_without_-100>/<message_id>`.
    """
    cid = str(chat_id)
    if cid.startswith("-100"):
        cid = cid[4:]
    return f"https://t.me/c/{cid}/{message_id}"


def _format_deadline(task: dict) -> str:
    dl = task.get('deadline')
    if not dl:
        return "—"
    try:
        dt = datetime.fromisoformat(dl) if isinstance(dl, str) else dl
        return dt.strftime('%d.%m')
    except Exception:
        return "—"


async def _get_design_cards() -> list[dict]:
    cards = await brain_client.get_cards()
    # выбираем только те карточки, которые уже были отправлены дизайнерам
    return [c for c in cards if c.get('prompt_message')]


async def _build_page(chat_id: int, page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    cards = await _get_design_cards()
    cards.sort(key=lambda x: x.get('deadline') or '')
    total = len(cards)

    if total == 0:
        return "❗️ В данный момент для дизайнеров задач нет.", None

    start = page * TASKS_PER_PAGE
    end = min(start + TASKS_PER_PAGE, total)
    rows = []
    for idx, card in enumerate(cards[start:end], start=start + 1):
        name = card.get('name', 'Без названия')
        dd = _format_deadline(card)
        link = _make_message_link(chat_id, card['prompt_message'])
        # Markdown-ссылка
        rows.append(f"[{idx}. {name} — до {dd}]({link})")

    text = f"*Задачи для дизайнеров ({start + 1}-{end}/{total}):*\n" + "\n".join(rows)

    # Формирование клавиатуры (только если есть кнопки)
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton('⬅️ Назад', callback_data=f'design_tasks_page:{page-1}'))
    if end < total:
        buttons.append(InlineKeyboardButton('Вперед ➡️', callback_data=f'design_tasks_page:{page+1}'))
    kb = None
    if buttons:
        kb = InlineKeyboardMarkup()
        kb.row(*buttons)

    return text, kb


@dp.message(Command('design_tasks'))
async def cmd_design_tasks(message: Message):
    """Команда для просмотра задач в группе дизайнеров."""
    if message.chat.id != DESIGN_GROUP:
        return

    logger.info(f"Design group command invoked by {message.from_user.id if message.from_user else None}")
    text, kb = await _build_page(message.chat.id, 0)
    await message.answer(text, reply_markup=kb, parse_mode='Markdown', disable_web_page_preview=True)


@dp.callback_query(lambda c: c.data and c.data.startswith('design_tasks_page:'))
async def _design_tasks_nav(query: CallbackQuery):
    # Навигация по страницам списка задач
    parts = query.data.split(':')
    if len(parts) != 2:
        await query.answer()
        return

    try:
        page = int(parts[1])
    except ValueError:
        await query.answer()
        return

    if query.message.chat.id != DESIGN_GROUP:
        await query.answer()
        return

    text, kb = await _build_page(query.message.chat.id, page)
    try:
        await query.message.edit_text(text, reply_markup=kb, parse_mode='Markdown', disable_web_page_preview=True)
    except Exception:
        # сообщение могло быть удалено или изменено, просто пропускаем
        pass
    await query.answer()
