from tg.oms.models.radio_page import RadioTypeScene
from modules.api_client import brain_api
from tg.oms.utils import callback_generator

class UserPage(RadioTypeScene):

    __page_name__ = 'user'
    __next_page__ = 'main'

    users = []

    async def data_preparate(self):
        await super().data_preparate()

        if not self.users:
            users, status = await brain_api.get(
                '/kaiten/get-users',
                params={'only_virtual': 1}
            )
            self.users = users

        self.options = {
            user['id']: user['full_name']
            for user in self.users
        }
    
    async def buttons_worker(self):
        buttons = await super().buttons_worker()
        
        buttons.append({
            'text': '❌ Сбросить',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'reset'
            ),
            'next_line': True
        })

        return buttons

    @RadioTypeScene.on_callback('reset')
    async def reset(self, callback, args):

        await self.scene.update_key('scene',
                                    self.scene_key, None)
        await self.scene.update_key(self.__page_name__,
                                    self.scene_key, None)

        await self.scene.update_page(self.__next_page__)