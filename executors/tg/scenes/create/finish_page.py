from tg.oms.utils import callback_generator
from tg.oms import Page
from modules.api_client import brain_api
from modules.constants import SETTINGS

class FinishPage(Page):

    __page_name__ = 'finish'


    def min_values(self):
        data = self.scene.data['scene']
        keys = ['name', 'description', 'publish_date']

        for key in keys:
            if data.get(key, None) in [None, '']:
                return False
        return True

    async def buttons_worker(self) -> list[dict]:
        buttons = []

        if self.min_values():
            buttons.append({
                'text': '❤ Создать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'end'),
                'ignore_row': True
            })

        return buttons
    
    async def content_worker(self) -> str:
        self.clear_content()
        content = await super().content_worker()

        if not self.min_values():
            content += '\n\n❗️ Не все обязательные поля заполнены. Пожалуйста, вернитесь и заполните их.'

        return content

    @Page.on_callback('end')
    async def on_end(self, callback, args):
        await callback.answer('Завершено!')
        data = self.scene.data['scene']

        res, status = await brain_api.post(
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

        if status:
            await self.scene.end()
            await self.scene.__bot__.send_message(
                self.scene.user_id,
                f'Задача успешно создана c ID: {res["id"]}'
            )