from tg.oms.models.option_page import OptionTypeScene
from modules.constants import SETTINGS
from modules.api_client import update_card

class ChannelsSettingsPage(OptionTypeScene):

    __page_name__ = 'channels-settings'
    __scene_key__ = 'clients_list'

    async def data_preparate(self):
        # Устанавливаем опции из настроек
        self.options = {
            key: client['name'] 
            for key, client in SETTINGS['properties']['channels']['values'].items()
        }
        
        # Копируем значения из сцены в страницу при первой загрузке
        clients_list = self.scene.data['scene'].get('clients_list', [])
        self.default_values = clients_list
        
        # Копируем в данные страницы
        await self.scene.update_key(self.__page_name__, 'clients_list', clients_list)
        
        await super().data_preparate()

    async def content_worker(self) -> str:
        # Получаем список выбранных каналов ИЗ ДАННЫХ СТРАНИЦЫ
        clients_list = self.scene.data[self.__page_name__].get('clients_list', [])
        
        # Преобразуем ключи в имена для отображения
        if clients_list:
            channel_names = []
            for channel_key in clients_list:
                channel_info = SETTINGS['properties']['channels']['values'].get(channel_key)
                if channel_info:
                    channel_names.append(channel_info['name'])
                else:
                    channel_names.append(channel_key)
            channels_text = ', '.join(channel_names)
        else:
            channels_text = 'Не указаны'
        
        return self.append_variables(channels=channels_text)

    @OptionTypeScene.on_callback('all')
    async def on_all(self, callback, args):
        # Получаем выбранные каналы ИЗ ДАННЫХ СТРАНИЦЫ (они обновляются в родительском классе)
        clients_list = self.scene.data[self.__page_name__].get('clients_list', [])
        
        # Синхронизируем данные страницы с данными сцены
        await self.scene.update_key('scene', 'clients_list', clients_list)
        
        # Обновляем карточку
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            await update_card(
                card_id=task_id,
                clients=clients_list
            )
        
        # Обновляем отображение в главной странице - преобразуем ключи в имена
        if clients_list:
            channel_names = []
            for channel_key in clients_list:
                channel_info = SETTINGS['properties']['channels']['values'].get(channel_key)
                if channel_info:
                    channel_names.append(channel_info['name'])
                else:
                    channel_names.append(channel_key)
            channels_text = ', '.join(channel_names)
        else:
            channels_text = 'Не указаны'
        
        await self.scene.update_key('scene', 'channels', channels_text)
        
        await self.scene.update_message()
