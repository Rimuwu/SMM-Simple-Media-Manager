from tg.oms import Page
from modules.api_client import update_card
from global_modules.classes.enums import CardStatus

class StatusSetterPage(Page):
    
    __page_name__ = 'status-setter'
    
    async def buttons_worker(self):
        buttons = await super().buttons_worker()
        
        # Добавляем кнопку для изменения статуса на "На проверке"
        from tg.oms.utils import callback_generator
        
        buttons.append({
            'text': '🔍 Отправить на проверку',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'set_review'
            )
        })
        
        return buttons
    
    @Page.on_callback('set_review')
    async def set_review_status(self, callback, args):
        """Изменяет статус задачи на "На проверке" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            # Обновляем статус в базе
            await update_card(
                card_id=task_id,
                status=CardStatus.review
            )
            
            # Обновляем отображение статуса
            await self.scene.update_key('scene', 'status', '🔍 На проверке')
            
            await callback.answer('✅ Статус изменен на "На проверке"', show_alert=True)
            
            # Возвращаемся на главную страницу
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
