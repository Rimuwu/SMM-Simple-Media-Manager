from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page


class UpdateTextPage(TextTypeScene):
    """
    Базовый класс для страниц с текстовым вводом и обновлением в БД.
    Наследники должны реализовать метод update_to_database.
    """

    @Page.on_text('str')
    async def handle_text(self, message, value: str):
        """Переопределяем обработчик текста для добавления обновления БД"""
        text = value.strip()
        self.clear_content()

        if len(text) < self.min_length:
            self.content += f"\n\nТекст слишком короткий. Минимальная длина: {self.min_length} символов."
            await self.scene.update_message()
            return

        if len(text) > self.max_length:
            self.content += f"\n\nТекст слишком длинный. Максимальная длина: {self.max_length} символов."
            await self.scene.update_message()
            return

        # Сохраняем текст в сцену
        await self.scene.update_key(
            'scene',
            self.scene_key, 
            text
        )

        # Сохраняем текст в страницу
        await self.scene.update_key(
            self.__page_name__,
            self.scene_key, 
            text
        )

        # Обновляем в базе данных
        if hasattr(self, 'update_to_database'):
            success = await self.update_to_database(text)
            if not success:
                self.content += "\n\n❌ Ошибка при сохранении. Попробуйте еще раз."
                await self.scene.update_message()
                return

        # Переходим к следующей странице
        if self.next_page:
            await self.scene.update_page(
                self.next_page)
        else:
            self.clear_content()
            await self.scene.update_message()

    async def update_to_database(self, value: str) -> bool:
        """
        Метод для обновления данных в БД.
        Должен быть переопределен в наследниках.
        
        Args:
            value: Новое значение текста
            
        Returns:
            True если обновление успешно, False в противном случае
        """
        raise NotImplementedError("Метод update_to_database должен быть реализован в наследнике")
