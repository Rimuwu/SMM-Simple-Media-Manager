from pprint import pprint
from typing import Optional
from ..utils import callback_generator
from .page import Page
from aiogram.types import CallbackQuery

class OptionTypeScene(Page):
    """Страница с выбором нескольких вариантов (checkbox).
    """

    __page_name__: str = ''
    __options__: dict = {} # 'key': 'text'
    __select_icon__: str = '✅'
    __scene_key__: str = 'option-type'
    __default_values__: Optional[list] = None
    __max_select__: int = 0  # 0 - неограниченно

    __json_args__ = [
        'options', 'scene_key', 'default_values',
        'select_icon', 'max_select'
    ]

    def __after_init__(self):
        self.options = self.__options__
        self.select_icon = self.__select_icon__
        self.default_values = self.__default_values__
        self.scene_key = self.__scene_key__
        self.max_select = self.__max_select__

    async def data_preparate(self):
        selected = self.scene.get_key(
            self.__page_name__, self.scene_key)

        if not selected:
            await self.scene.update_key(
                'scene',
                self.scene_key, 
                self.default_values or []
            )
            await self.scene.update_key(
                self.__page_name__,
                self.scene_key, 
                self.default_values or []
            )


    async def buttons_worker(self):
        buttons = []
        selected = self.scene.get_key(
            self.__page_name__, self.scene_key)

        for key, text in self.options.items():
            if key in selected:
                text = f"{self.select_icon} {text}"

            buttons.append({
                'text': text,
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'option', key)
            })

        return buttons

    @Page.on_callback('option')
    async def handle_int(self, callback: CallbackQuery, args: list):
        value = args[1]

        scene_data = self.scene.get_key(
            'scene',
            self.scene_key
        )

        if self.max_select > 0 and len(scene_data) >= self.max_select and value not in scene_data:
            # Превышено максимальное количество выборов
            await callback.answer(f"Максимальное количество выборов: {self.max_select}", show_alert=True)
            return

        if value in scene_data:
            scene_data.remove(value)
        else:
            scene_data.append(value)

        # Сохраняем текст в сцену
        await self.scene.update_key(
            'scene',
            self.scene_key, 
            scene_data
        )

        page_data = self.scene.get_key(
            self.__page_name__,
            self.scene_key
        )

        if value in page_data:
            page_data.remove(value)
        else:
            page_data.append(value)

        # Сохраняем текст в сцену
        await self.scene.update_key(
            self.__page_name__,
            self.scene_key, 
            page_data
        )

        await self.scene.update_message_markup()