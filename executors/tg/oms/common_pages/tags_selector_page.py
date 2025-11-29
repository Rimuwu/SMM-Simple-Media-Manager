from tg.oms.models.option_page import OptionTypeScene
from modules.constants import SETTINGS
from typing import Optional, Callable


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
        # Устанавливаем опции из настроек
        self.options = {
            key: tag['name'] 
            for key, tag in SETTINGS['properties']['tags']['values'].items()
        }

        # Копируем значения из сцены в страницу при первой загрузке
        tags_list = self.scene.data['scene'].get(self.scene_key, [])
        self.default_values = tags_list
        
        # Копируем в данные страницы
        await self.scene.update_key(self.__page_name__, self.scene_key, tags_list)

        await super().data_preparate()

    async def content_worker(self) -> str:
        # Получаем список выбранных тегов ИЗ ДАННЫХ СТРАНИЦЫ
        tags_list = self.scene.data[self.__page_name__].get(self.scene_key, [])
        
        # Преобразуем ключи в имена для отображения
        if tags_list:
            tag_names = []
            for tag_key in tags_list:
                tag_info = SETTINGS['properties']['tags']['values'].get(tag_key)
                if tag_info:
                    tag_names.append(tag_info['name'])
                else:
                    tag_names.append(tag_key)
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

        # Если нужно обновить в БД
        if self.update_to_db:
            success = await self.update_to_database(tags_list)
            
            if success:
                await callback.answer("✅ Теги обновлены")
                
                # Выполняем callback если есть
                if self.on_success_callback:
                    await self.on_success_callback(callback, tags_list)
            else:
                await callback.answer("❌ Ошибка при обновлении")
                return
        
        await self.scene.update_message()
    
    async def update_to_database(self, tags_list: list) -> bool:
        """
        Метод для обновления данных в БД.
        Переопределяется в дочерних классах.
        """
        return True
