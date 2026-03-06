from tg.oms.models.page import Page
from tg.oms.utils import callback_generator

class CancelPage(Page):

    __page_name__ = 'cancel'

    async def buttons_worker(self):
        buttons = await super().buttons_worker()

        buttons.append({
            'text': '❌ Удалить',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'reset'
            ),
            'next_line': True,
            'style': 'danger'
        })

        return buttons

    @Page.on_callback('reset')
    async def reset(self, callback, args):
        
        await self.scene.end()