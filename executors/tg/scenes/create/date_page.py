from tg.oms import Page

class DatePage(Page):
    
    __page_name__ = 'publish-date'
    
    @Page.on_text('not_handled')
    async def not_handled(self, message):

        self.clear_content()
        self.content += f'\n\n❗️ Некорректный формат даты. Попробуйте еще раз.'
        await self.scene.update_message()

    @Page.on_text('time')
    async def handle_time(self, message, value):

        await self.scene.update_key(
            'scene',
            'publish_date',
            value.isoformat()
        )
        await self.scene.update_page('main')