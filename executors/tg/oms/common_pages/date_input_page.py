from tg.oms import Page
from aiogram.types import Message
from typing import Optional, Callable


class DateInputPage(Page):
    """
    Базовый класс для страниц ввода даты/времени.
    
    Attributes:
        update_to_db: Если True, обновляет данные через API после установки
        on_success_callback: Опциональная функция для выполнения после успешного обновления
    """
    
    update_to_db: bool = False
    on_success_callback: Optional[Callable] = None
    __scene_key__: str
    __next_page__: str

    async def data_preparate(self) -> None:
        self.clear_content()

    async def content_worker(self) -> str:
        
        date = self.scene.data['scene'].get(self.__scene_key__)
        if date:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date)
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                formatted_date = date
        else:
            formatted_date = 'Не установлена'

        content = self.append_variables(
            **{
                self.__scene_key__: formatted_date
            }
        )
        return content

    @Page.on_text('not_handled')
    async def not_handled(self, message: Message):
        """Обработка некорректного формата даты"""
        self.clear_content()
        self.content += f'\n\n❗️ Некорректный формат даты. Попробуйте еще раз.'
        await self.scene.update_message()

    @Page.on_text('time')
    async def handle_time(self, message: Message, value):
        """Обработка корректной даты"""
        # Сохраняем в сцену
        await self.scene.update_key(
            'scene',
            self.__scene_key__,
            value.isoformat()
        )
        
        # Если нужно обновить в БД
        if self.update_to_db:
            success = await self.update_to_database(value)
            
            if success:
                # Выполняем callback если есть
                if self.on_success_callback:
                    await self.on_success_callback(message, value)
            else:
                await message.answer("❌ Ошибка при обновлении")
                return
        
        # Переходим на следующую страницу
        await self.scene.update_page(self.__next_page__)
    
    async def update_to_database(self, value) -> bool:
        """
        Метод для обновления данных в БД.
        Переопределяется в дочерних классах.
        """
        return True
