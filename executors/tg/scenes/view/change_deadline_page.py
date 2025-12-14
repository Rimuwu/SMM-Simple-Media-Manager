from tg.oms.common_pages import DateInputPage
from global_modules.brain_client import brain_client
from datetime import datetime


class ChangeDeadlinePage(DateInputPage):
    
    __page_name__ = 'change-deadline'
    __scene_key__ = 'deadline'
    __next_page__ = 'task-detail'

    update_to_db = True

    async def content_worker(self) -> str:
        task = self.scene.data['scene'].get('current_task_data', {})
        deadline = task.get('deadline')
        
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
                deadline_str = deadline_dt.strftime('%d.%m.%Y %H:%M')
            except:
                deadline_str = deadline
        else:
            deadline_str = 'Не установлен'
            
        self.content = self.append_variables(deadline=deadline_str)
        return self.content

    async def update_to_database(self, value) -> bool:
        """Обновляем дедлайн в карточке"""
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')

        # Получаем user_id текущего пользователя
        telegram_id = self.scene.user_id
        users = await brain_client.get_users(telegram_id=telegram_id)
        author_id = None
        if users and isinstance(users, list) and len(users) > 0:
            user = users[0]
            if isinstance(user, dict):
                author_id = user.get('user_id')
        
        # Обновляем дедлайн в карточке
        card = await brain_client.update_card(
            card_id=card_id,
            deadline=value.isoformat(),
            author_id=str(author_id) if author_id else None
        )
        status = card is not None

        if status:
            # Обновляем данные задачи
            task['deadline'] = value.isoformat()
            await self.scene.update_key(
                'scene', 'current_task_data', task)
            return True
        
        return False
