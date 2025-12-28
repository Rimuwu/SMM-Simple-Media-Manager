from pprint import pprint
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from tg.filters.authorize import Authorize
from tg.filters.role_filter import RoleFilter
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from global_modules.brain_client import brain_client
from global_modules.api_client import APIClient

executors_api = APIClient('http://executors:8003')

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot


@dp.message(Command("test_postmessage"), 
            RoleFilter("admin"))
async def test_postmessage(message: Message):

    uuid = message.text.split(" ")[1] if len(message.text.split(" ")) > 1 else None
    
    if not uuid:
        card = await brain_client.get_cards()
        uuid = card[0]['card_id'] if card else None
    
    card = await brain_client.get_cards(card_id=uuid)
    if not card:
        await message.answer(f"❌ Задача с ID {uuid} не найдена.")
        return

    card = card[0]
    
    for key in ['tg_main', 'vk_main']:

        data = {
            "card_id": card['card_id'],
            "client_key": key,
            "entities": [card['entities']],
            'post_images': card['post_images'],
            'content': card['content'].get(key, 
                                           card['content'].get('all', '-')),
            'tags': card['tags'],
            'settings': card['clients_settings']
        }
        
        res, status = await executors_api.post(
            '/post/send',
            data=data
        )
        logs = res.get('logs', [])
        pprint(logs)

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@dp.message(Command("test_url_button"), 
            RoleFilter("admin"))
async def test_url_button(message: Message):
    
    buttons = [
        [InlineKeyboardButton(
            text="Visit OpenAI",
            url="https://www.openai.com"
        )],
        [InlineKeyboardButton(
            text="Visit OpenAI",
            url="https://www.openai.com"
        )]
    ]
    
    msg = await message.answer(
        "Click the button below to visit OpenAI:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )
