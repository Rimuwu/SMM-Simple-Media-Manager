from tg.oms.models.option_page import OptionTypeScene
from typing import Optional, Callable


async def _get_tags_options() -> dict:
    """Загружает теги из БД, при отсутствии — из settings.json."""

    from models.Tag import Tag
    db_tags = [t.to_dict() for t in await Tag.all_sorted()]

    return {t['key']: t['name'] for t in db_tags}



class TagsSelectorPage(OptionTypeScene):
    """
    Базовый класс для страниц выбора тегов.
    
    Attributes:
        update_to_db: Если True, обновляет данные через API после выбора
        on_success_callback: Опциональная функция для выполнения после успешного обновления
    """
    
    update_to_db: bool = False
    on_success_callback: Optional[Callable] = None

    async def data_preparate(self):
        # Загружаем теги из БД (или fallback settings.json)
        self.options = await _get_tags_options()

        # Копируем значения из сцены в страницу при первой загрузке
        tags_list = self.scene.data['scene'].get(self.scene_key, [])
        self.default_values = tags_list
        
        # Копируем в данные страницы
        await self.scene.update_key(self.__page_name__, self.scene_key, tags_list)

        await super().data_preparate()

    async def content_worker(self) -> str:
        # Получаем список выбранных тегов ИЗ ДАННЫХ СТРАНИЦЫ
        tags_list = self.scene.data[self.__page_name__].get(self.scene_key, [])

        # Преобразуем ключи в имена для отображения через self.options
        if tags_list:
            tag_names = [self.options.get(key, key) for key in tags_list]
            tags_text = ', '.join(tag_names)
        else:
            tags_text = 'Не указаны'

        return self.append_variables(tags=tags_text)

    @OptionTypeScene.on_callback('all')
    async def on_all(self, callback, args):
        # Получаем выбранные теги ИЗ ДАННЫХ СТРАНИЦЫ
        tags_list = self.scene.data[self.__page_name__].get(self.scene_key, [])

        # Синхронизируем данные страницы с данными сцены
        await self.scene.update_key('scene', self.scene_key, tags_list)
        
        await self.scene.update_message()
    
    async def page_leave(self) -> None:
        """Обновляем данные в БД при выходе со страницы"""
        # Получаем выбранные теги из данных сцены
        tags_list = self.scene.data['scene'].get(self.scene_key, [])
        
        # Если нужно обновить в БД
        if self.update_to_db:
            success = await self.update_to_database(tags_list)
            
            if success and self.on_success_callback:
                # Выполняем callback если есть
                await self.on_success_callback(None, tags_list)
    
    async def update_to_database(self, tags_list: list) -> bool:
        """
        Метод для обновления данных в БД.
        Переопределяется в дочерних классах.
        """
        return True
