from tg.oms import Page
from global_modules.brain_client import brain_client

class PublishDateSetterPage(Page):
    
    __page_name__ = 'publish-date-setter'
    
    @Page.on_text('not_handled')
    async def not_handled(self, message):
        self.clear_content()
        self.content += f'\n\n❗️ Некорректный формат даты. Попробуйте еще раз.'
        await self.scene.update_message()

    @Page.on_text('time')
    async def handle_time(self, message, value):
        # Сохраняем дату в ISO формате
        iso_date = value.isoformat()
        
        await self.scene.update_key('scene', 'send_time', iso_date)
        
        # Форматируем для отображения
        display_date = value.strftime('%d.%m.%Y %H:%M')
        await self.scene.update_key('scene', 'publish_date', display_date)
        
        # Обновляем карточку
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            await brain_client.update_card(
                card_id=task_id,
                send_time=iso_date
            )
        
        await self.scene.update_page('main-page')
