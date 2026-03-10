from modules.card import card_events
from uuid import UUID as _UUID
from tg.oms.common_pages.update_text_page import UpdateTextPage


class ChangeNamePage(UpdateTextPage):
    
    __page_name__ = 'change-name'
    __scene_key__ = 'task_name'
    __next_page__ = 'task-detail'

    async def data_preparate(self):
        """Подгружаем текущее название задачи"""
        task = self.scene.data['scene'].get('current_task_data')
        if task:
            current_name = task.get('name', '')
            await self.scene.update_key('scene', 'task_name', current_name)

        await super().data_preparate()

    async def content_worker(self) -> str:
        task = self.scene.data['scene'].get('current_task_data', {})
        current_name = task.get('name', 'Без названия')

        self.content = self.append_variables(task_name=current_name)
        return self.content

    async def update_to_database(self, value: str) -> bool:
        """Обновляем название в карточке"""
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')

        try:
            await card_events.on_name(new_name=value, card_id=_UUID(str(card_id)))
        except Exception:
            return False

        # Обновляем локальный кэш сцены
        task['name'] = value
        await self.scene.update_key('scene', 'current_task_data', task)
        return True
