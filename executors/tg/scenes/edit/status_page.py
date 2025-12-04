from tg.oms import Page
from modules.api_client import update_card, get_cards
from global_modules.classes.enums import CardStatus
from tg.oms.utils import callback_generator
from modules.logs import executors_logger as logger

class StatusSetterPage(Page):
    
    __page_name__ = 'status-setter'
    
    async def buttons_worker(self):
        buttons = await super().buttons_worker()
        
        # Получаем текущий статус задачи
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            cards = await get_cards(card_id=task_id)
            if cards:
                card = cards[0]
                status = card.get('status')
                
                # Если статус "Создано" - кнопка "Взять в работу"
                if status == CardStatus.pass_.value:
                    buttons.append({
                        'text': '✏️ Взять в работу',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_edited'
                        )
                    })
                
                # Если статус "В работе" - кнопка "Отправить на проверку"
                elif status == CardStatus.edited.value:
                    buttons.append({
                        'text': '🔍 Отправить на проверку',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_review'
                        )
                    })
                
                # Если статус "На проверке" - 2 кнопки
                elif status == CardStatus.review.value:
                    buttons.append({
                        'text': '✅ Завершить',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_ready'
                        )
                    })
                    buttons.append({
                        'text': '🔙 Вернуть на доработку',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_edited'
                        )
                    })
        
        return buttons
    
    @Page.on_callback('set_edited')
    async def set_edited_status(self, callback, args):
        """Изменяет статус задачи на "В работе" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} перевел задачу {task_id} в статус 'В работе'")
            await update_card(card_id=task_id, status=CardStatus.edited)
            await self.scene.update_key('scene', 'status', '✏️ В работе')
            await callback.answer('✅ Статус изменен на "В работе"', show_alert=True)
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_review')
    async def set_review_status(self, callback, args):
        """Изменяет статус задачи на "На проверке" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} отправил задачу {task_id} на проверку")
            await update_card(card_id=task_id, status=CardStatus.review)
            await self.scene.update_key('scene', 'status', '🔍 На проверке')
            await callback.answer('✅ Статус изменен на "На проверке"', show_alert=True)
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_ready')
    async def set_ready_status(self, callback, args):
        """Изменяет статус задачи на "Готова" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} завершил задачу {task_id} (статус 'Готова')")
            await update_card(card_id=task_id, status=CardStatus.ready)
            await self.scene.update_key('scene', 'status', '✅ Готова')
            await callback.answer('✅ Задача завершена!', show_alert=True)
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
