from tg.oms.models.option_page import OptionTypeScene
from modules.constants import SETTINGS

class TagsPage(OptionTypeScene):

    __page_name__ = 'tags'

    async def data_preparate(self):
        await super().data_preparate()

        self.options = {
            key: client['name'] 
            for key, client in SETTINGS['properties']['tags']['values'].items()
        }

    @OptionTypeScene.on_callback('all')
    async def on_all(self, callback, args):
        await self.scene.update_message()
