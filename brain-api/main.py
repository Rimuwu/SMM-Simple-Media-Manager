from pprint import pprint
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from database.core import create_superuser, create_tables
from global_modules.limiter import limiter
from global_modules.middlewares.logs_mid import RequestLoggingMiddleware

from routers.standart import router as standart_router
# from routers.user import router as user_router
from routers.card import router as card_router
from routers.ai import router as ai_router

from global_modules.api_configurate import get_fastapi_app

from modules.logs import brain_logger
from modules.kaiten import kaiten
from modules.config_kaiten import sync_kaiten_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    brain_logger.info("API is starting up...")
    brain_logger.info("Creating missing tables on startup...")
    await create_tables()
    await create_superuser()
    
    # await kaiten_check()
    
    # await sync_kaiten_settings()
    
    yield

    # Shutdown

app = get_fastapi_app(
    title="API",
    version="1.0.0",
    description="Brain API",
    debug=False,
    lifespan=lifespan,
    limiter=True,
    middlewares=[],
    routers=[
        standart_router, card_router, ai_router
    ],
    api_logger=brain_logger
)
app.add_middleware(RequestLoggingMiddleware, logger=brain_logger)

async def kaiten_check():

    async with kaiten as client:
        # boards = await client.get_boards(656548)
        # pprint(boards)
        
        # columns = await client.get_columns(1490862)
        # pprint(columns)
        
        # properties = await client.get_custom_properties()

        # pprint(properties)

        # card = await client.get_card(56247840)
        # pprint(card)
        
        # card2 = await client.get_card(56248185)
        # pprint(card2)
        
        us = await client.get_company_users(only_virtual=True)
        print(us)

        # pr_v = await client.get_property_select_values(496988)

        # pprint(pr_v)
        
        # pp = await client.get_custom_properties()
        # pprint(pp)

# async def test_db():
#     from models.User import User
#     from models.Card import Card
#     from models.Automation import Automation, Preset
#     from uuid import uuid4

#     # Создание пользователя
    
#     user, status = await User.first_or_create(
#         user_id=uuid4(),
#         telegram_id=123456789,
#     )
#     pprint(user.to_dict())
    
#     await user.update(telegram_id=987654321)
#     pprint(user.to_dict())
    
#     user = await User.get_by_id(user.user_id)
#     if user:
#         pprint(user.to_dict())