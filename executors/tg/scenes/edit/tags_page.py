from tg.oms.models.option_page import OptionTypeScene
from modules.constants import SETTINGS
from modules.api_client import update_card
from aiogram.types import CallbackQuery

class TagsSetterPage(OptionTypeScene):

    __page_name__ = 'tags-setter'
    __scene_key__ = 'tags_list'

    async def data_preparate(self):
        # Устанавливаем опции из настроек
        self.options = {
            key: tag['name'] 
            for key, tag in SETTINGS['properties']['tags']['values'].items()
        }

        # Копируем значения из сцены в страницу при первой загрузке
        tags_list = self.scene.data['scene'].get('tags_list', [])
        self.default_values = tags_list
        
        # Копируем в данные страницы
        await self.scene.update_key(self.__page_name__, 'tags_list', tags_list)

        await super().data_preparate()

    async def content_worker(self) -> str:
        # Получаем список выбранных тегов ИЗ ДАННЫХ СТРАНИЦЫ
        tags_list = self.scene.data[self.__page_name__].get('tags_list', [])
        
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
        # Получаем выбранные теги ИЗ ДАННЫХ СТРАНИЦЫ (они обновляются в родительском классе)
        tags_list = self.scene.data[self.__page_name__].get('tags_list', [])
        print(tags_list)

        scene_tags = self.scene.data['scene'].get('tags_list', [])
        print(scene_tags)

        # # Синхронизируем данные страницы с данными сцены
        # await self.scene.update_key('scene', 'tags_list', tags_list)

        # Обновляем карточку
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            await update_card(
                card_id=task_id,
                tags=tags_list
            )

        # # Обновляем отображение в главной странице - преобразуем ключи в имена
        # if tags_list:
        #     tag_names = []
        #     for tag_key in tags_list:
        #         tag_info = SETTINGS['properties']['tags']['values'].get(tag_key)
        #         if tag_info:
        #             tag_names.append(tag_info['name'])
        #         else:
        #             tag_names.append(tag_key)
        #     tags_text = ', '.join(tag_names)
        # else:
        #     tags_text = 'Не указаны'
        
        # await self.scene.update_key('scene', 'tags', tags_text)
        
        # await self.scene.update_message()
