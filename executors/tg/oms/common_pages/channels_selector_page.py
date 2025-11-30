from tg.oms.models.option_page import OptionTypeScene
from modules.constants import SETTINGS
from typing import Optional, Callable


class ChannelsSelectorPage(OptionTypeScene):
    """
    Базовый класс для страниц выбора каналов.
    
    Attributes:
        update_to_db: Если True, обновляет данные через API после выбора
        on_success_callback: Опциональная функция для выполнения после успешного обновления
    """
    
    update_to_db: bool = False
    on_success_callback: Optional[Callable] = None

    async def data_preparate(self):
        # Устанавливаем опции из настроек
        self.options = {
            key: client['name'] 
            for key, client in SETTINGS['properties']['channels']['values'].items()
        }

        # Копируем значения из сцены в страницу при первой загрузке
        channels_list = self.scene.data['scene'].get(self.scene_key, [])
        self.default_values = channels_list
        
        # Копируем в данные страницы
        await self.scene.update_key(self.__page_name__, self.scene_key, channels_list)

        await super().data_preparate()

    async def content_worker(self) -> str:
        # Получаем список выбранных каналов ИЗ ДАННЫХ СТРАНИЦЫ
        channels_list = self.scene.data[self.__page_name__].get(self.scene_key, [])
        
        # Преобразуем ключи в имена для отображения
        if channels_list:
            channel_names = []
            for ch_key in channels_list:
                ch_info = SETTINGS['properties']['channels']['values'].get(ch_key)
                if ch_info:
                    channel_names.append(ch_info['name'])
                else:
                    channel_names.append(ch_key)
            channels_text = ', '.join(channel_names)
        else:
            channels_text = 'Не указаны'
        
        # Заменяем {channels} в контенте (если есть) или просто возвращаем контент
        # Но OptionTypeScene обычно использует self.content
        # Мы можем обновить self.content, подставив значения
        
        # В базовом классе content_worker может быть не реализован или делать что-то другое.
        # OptionTypeScene наследуется от Page.
        
        # Если в контенте есть {channels}, заменим его
        original_content = self.content
        if '{channels}' in original_content:
            return original_content.format(channels=channels_text)
            
        return original_content

    @OptionTypeScene.on_callback('all')
    async def on_all(self, callback, args):
        """Выбрать все каналы"""
        all_keys = list(self.options.keys())
        current_keys = self.scene.data[self.__page_name__].get(self.scene_key, [])
        
        if set(current_keys) == set(all_keys):
            # Если все выбраны - снимаем выбор
            new_keys = []
        else:
            # Иначе выбираем все
            new_keys = all_keys
            
        await self.scene.update_key(self.__page_name__, self.scene_key, new_keys)
        await self.scene.update_message()
