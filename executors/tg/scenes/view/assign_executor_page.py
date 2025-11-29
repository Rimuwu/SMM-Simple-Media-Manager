from tg.oms.common_pages import UserSelectorPage
from modules.api_client import update_card


class AssignExecutorPage(UserSelectorPage):

    __page_name__ = 'assign-executor'
    __scene_key__ = 'executor_id'
    __next_page__ = 'task-detail'
    
    update_to_db = True
    allow_reset = True
    
    async def update_to_database(self, user_id) -> bool:
        """Обновляем исполнителя в карточке"""
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')
        
        # Обновляем карточку
        success = await update_card(
            card_id=card_id,
            executor_id=user_id
        )

        if success:
            # Обновляем данные задачи
            task['executor_id'] = user_id
            
            # Обновляем информацию об исполнителе
            if user_id:
                selected_user = next((u for u in self.users_data if str(u['user_id']) == user_id), None)
                if selected_user:
                    telegram_id = selected_user.get('telegram_id')
                    tasker_id = selected_user.get('tasker_id')
                    
                    kaiten_name = self.kaiten_users.get(tasker_id) if tasker_id else None
                    
                    task['executor'] = {
                        'user_id': user_id,
                        'telegram_id': telegram_id,
                        'tasker_id': tasker_id,
                        'full_name': kaiten_name or f"@{telegram_id}"
                    }
            else:
                task['executor'] = None
            
            await self.scene.update_key('scene', 'current_task_data', task)
            return True
        
        return False
