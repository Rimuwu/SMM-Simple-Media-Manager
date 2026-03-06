import aiogram
from ..utils import callback_generator
from .page import Page

class RadioTypeScene(Page):
    """Страница с выбором из нескольких вариантов (radio).
    Поддерживает постраничный вывод (похож на OptionTypeScene) при указании
    `__max_on_page__` и настраиваемые иконки навигации.
    """

    __page_name__: str = ''
    __options__: dict = {} # 'key': 'text'
    __select_icon__: str = '✅'
    __scene_key__: str = 'radio-type'
    __default_value__: str = ''
    __next_page__: str = ''

    # Параметры пагинации
    __max_on_page__: int = 0  # 0 - все на одной странице
    __prev_page_icon__: str = '◀️'
    __next_page_icon__: str = '▶️'
    __separator__: bool = False

    __json_args__ = [
        'options', 'scene_key', 'default_value',
        'next_page', 'select_icon', 'max_on_page',
        'prev_page_icon', 'next_page_icon', 'separator'
    ]

    def __after_init__(self):
        self.options = self.__options__
        self.select_icon = self.__select_icon__
        self.default_value = self.__default_value__
        self.scene_key = self.__scene_key__
        self.next_page = self.__next_page__
        self.max_on_page = self.__max_on_page__
        self.prev_page_icon = self.__prev_page_icon__
        self.next_page_icon = self.__next_page_icon__
        self.separator = self.__separator__

    async def data_preparate(self):
        selected = self.scene.get_key(
            self.__page_name__, self.scene_key)
        if not selected:

            await self.scene.update_key(
                'scene',
                self.scene_key, 
                self.default_value
            )
            await self.scene.update_key(
                self.__page_name__,
                self.scene_key, 
                self.default_value
            )

        # Инициализация текущей страницы для пагинации
        current_page = self.scene.get_key(
            self.__page_name__, 'current_page')

        if current_page is None:
            await self.scene.update_key(
                self.__page_name__,
                'current_page', 
                0
            )


    async def buttons_worker(self):
        buttons = []
        selected = self.scene.get_key(
            self.__page_name__, self.scene_key)

        # Если пагинация включена
        if self.max_on_page > 0:
            options_list = list(self.options.items())
            total_options = len(options_list)
            total_pages = (total_options + self.max_on_page - 1) // self.max_on_page

            # Текущая страница
            current_page = self.scene.get_key(
                self.__page_name__, 'current_page') or 0

            # Корректируем, если выйдем за пределы
            if current_page >= total_pages and total_pages > 0:
                current_page = total_pages - 1
                await self.scene.update_key(
                    self.__page_name__, 'current_page', current_page
                )

            start_idx = current_page * self.max_on_page
            end_idx = min(start_idx + self.max_on_page, total_options)

            page_options = options_list[start_idx:end_idx]

            for key, text in page_options:
                if selected == key:
                    text = f"{self.select_icon} {text}"

                buttons.append({
                    'text': text,
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'radio', key)
                })

            # Навигация между страницами
            if total_pages > 1:
                nav_buttons = []

                nav_buttons.append({
                    'text': self.prev_page_icon,
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'prev_page'),
                    'next_line': True
                })

                nav_buttons.append({
                    'text': self.next_page_icon,
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'next_page')
                })

                if self.separator:
                    nav_buttons.append({
                        'text': ' ',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            ' '),
                        'ignore_row': True
                    })

                buttons.extend(nav_buttons)

            return buttons

        # Без пагинации - все опции
        for key, text in self.options.items():
            if selected == key:
                text = f"{self.select_icon} {text}"

            buttons.append({
                'text': text,
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'radio', key)
            })

        return buttons

    async def on_selected(self, callback, selected_value):
        """Метод для переопределения в дочерних классах.
        Вызывается после выбора значения.
        """
        # Переходим к следующей странице
        if self.next_page:
            await self.scene.update_page(self.next_page)
        else:
            await self.scene.update_message_markup()

    @Page.on_callback('radio')
    async def handle_int(self, callback, args: list):
        value = args[1]

        # Сохраняем текст в сцену
        await self.scene.update_key(
            'scene',
            self.scene_key, 
            value
        )

        # Сохраняем текст в страницу
        await self.scene.update_key(
            self.__page_name__,
            self.scene_key, 
            value
        )

        # Вызываем метод для переопределения
        await self.on_selected(callback, value)

    @Page.on_callback('prev_page')
    async def handle_prev_page(self, callback, args: list):
        """Обработчик кнопки 'предыдущая страница'"""
        current_page = self.scene.get_key(
            self.__page_name__, 'current_page') or 0

        if current_page > 0:
            await self.scene.update_key(
                self.__page_name__,
                'current_page', 
                current_page - 1
            )
            await self.scene.update_message_markup()
        else:
            # перейти на последнюю страницу при попытке уйти назад с первой
            if self.max_on_page > 0:
                total_options = len(self.options)
                total_pages = (total_options + self.max_on_page - 1) // self.max_on_page
                if total_pages > 1:
                    await self.scene.update_key(
                        self.__page_name__,
                        'current_page', 
                        total_pages - 1
                    )
                    await self.scene.update_message_markup()

    @Page.on_callback('next_page')
    async def handle_next_page(self, callback, args: list):
        """Обработчик кнопки 'следующая страница'"""
        current_page = self.scene.get_key(
            self.__page_name__, 'current_page') or 0

        if self.max_on_page > 0:
            total_options = len(self.options)
            total_pages = (total_options + self.max_on_page - 1) // self.max_on_page

            if current_page < total_pages - 1:
                await self.scene.update_key(
                    self.__page_name__,
                    'current_page', 
                    current_page + 1
                )
                await self.scene.update_message_markup()
            else:
                await self.scene.update_key(
                    self.__page_name__,
                    'current_page', 
                    0
                )
                await self.scene.update_message_markup()