from typing import Union
from aiogram.types import Message, CallbackQuery
from aiogram import Dispatcher

from .utils import CALLBACK_PREFIX
from .manager import scene_manager
from aiogram import F, Router
from logging import getLogger
from .filters.scene_filter import InScene

logger = getLogger(__name__)

def register_handlers(router: Union[Router, Dispatcher]):

    @router.message(InScene(), F.photo)
    async def on_photo_message(message: Message):
        """Обработчик фото-сообщений в сцене"""
        user_id = message.from_user.id
        scene = scene_manager.get_scene(user_id)
        logger.info(f"[OMS] on_photo_message called for user {user_id}, scene={scene is not None}")

        if message.chat.id == user_id:
            if scene:
                logger.info(f"[OMS] Calling scene.text_handler for photo")
                await scene.text_handler(message)

    @router.message(InScene(), F.document)
    async def on_document_message(message: Message):
        """Обработчик документов в сцене"""
        user_id = message.from_user.id
        scene = scene_manager.get_scene(user_id)

        if message.chat.id == user_id:
            if scene:
                await scene.text_handler(message)

    @router.message(InScene(), F.video)
    async def on_video_message(message: Message):
        """Обработчик видео в сцене"""
        user_id = message.from_user.id
        scene = scene_manager.get_scene(user_id)

        if message.chat.id == user_id:
            if scene:
                await scene.text_handler(message)

    @router.message(InScene())
    async def on_message(message: Message):
        user_id = message.from_user.id
        scene = scene_manager.get_scene(user_id)

        if message.chat.id == user_id:

            if scene:
                await scene.text_handler(message)

    @router.callback_query(
        InScene(),
        F.data.split(":")[:2] == [CALLBACK_PREFIX, 'to_page']
    )
    async def to_page(callback: CallbackQuery):
        user_id = callback.from_user.id
        user_session = scene_manager.get_scene(user_id)

        prefix, c_type, scene_name, *args = callback.data.split(':')
        to_page = args[0]

        if user_session:
            status, answer = await user_session.update_page(to_page)
            if not status:
                await callback.answer(answer, show_alert=True)

    @router.callback_query(
        InScene(),
        F.data.split(":")[0] == CALLBACK_PREFIX)
    async def on_callback_query(callback: CallbackQuery):
        user_id = callback.from_user.id
        user_session = scene_manager.get_scene(user_id)

        prefix, c_type, scene_name, *args = callback.data.split(':')

        if user_session:
            # Передаем c_type как первый элемент args, остальные аргументы следом
            callback_args = [c_type] + args
            await user_session.callback_handler(callback, callback_args)