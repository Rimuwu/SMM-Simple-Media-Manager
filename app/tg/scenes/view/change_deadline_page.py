from tg.oms.common_pages import DateInputPage
from modules import card_events
from uuid import UUID as _UUID
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

        old_deadline_raw = task.get('deadline')
        old_deadline = datetime.fromisoformat(old_deadline_raw) if old_deadline_raw else None

        try:
            await card_events.on_deadline(
                new_deadline=value,
                old_deadline=old_deadline,
                card_id=_UUID(str(card_id))
            )
        except Exception:
            return False

        # Обновляем локальный кэш сцены
        task['deadline'] = value.isoformat()
        await self.scene.update_key('scene', 'current_task_data', task)
        return True
