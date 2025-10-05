from tg.oms.utils import callback_generator
from tg.oms import Page
from modules.api_client import brain_api
from modules.constants import SETTINGS

class FinishPage(Page):

    __page_name__ = 'finish'
    
    async def buttons_worker(self) -> list[dict]:
        buttons = []
        if all(key in self.scene.data for key in ['name', 'description', 'publish_date']):
            buttons.append({
                'text': '❤ Создать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'end'),
                'ignore_row': True
            })

        return buttons
    
    async def content_worker(self) -> str:
        content = await super().content_worker()

        if not all(key in self.scene.data for key in ['name', 'description', 'publish_date']):
            content += '\n\n❗️ Не все обязательные поля заполнены. Пожалуйста, вернитесь и заполните их.'
            return content

    @Page.on_callback('end')
    async def on_end(self, callback, args):
        await callback.answer('Завершено!')
        data = self.scene.data['scene']

        res = await brain_api.post(
            '/card/create',
            data={
                'title': data['name'],
                'description': data['description'],
                'deadline': data['publish_date'],
                'channels': data['channels'],
                'editor_check': True,
                'image_prompt': data['image'],
                'tags': data['tags'],
                'type_id': data['type']
            }
        )
        print(res)