from tg.oms.common_pages import DateInputPage
from modules.api_client import update_card


class ChangeDeadlinePage(DateInputPage):
    
    __page_name__ = 'change-deadline'
    __scene_key__ = 'deadline'
    __next_page__ = 'task-detail'
    
    update_to_db = True
    
    async def update_to_database(self, value) -> bool:
        """Обновляем дедлайн в карточке"""
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')
        
        # Обновляем дедлайн в карточке
        success = await update_card(
            card_id=card_id,
            deadline=value.isoformat()
        )

        if success:
            # Обновляем данные задачи
            task['deadline'] = value.isoformat()
            await self.scene.update_key('scene', 'current_task_data', task)
            return True
        
        return False
