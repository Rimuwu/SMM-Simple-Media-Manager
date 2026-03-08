from modules.card import card_events
from uuid import UUID as _UUID
from tg.oms.common_pages.update_text_page import UpdateTextPage
from modules.enums import ChangeType


class ChangeDescriptionPage(UpdateTextPage):
    
    __page_name__ = 'change-description'
    __scene_key__ = 'task_description'
    __next_page__ = 'task-detail'

    async def data_preparate(self):
        """Подгружаем текущее описание задачи"""
        task = self.scene.data['scene'].get('current_task_data')
        if task:
            current_description = task.get('description', '')
            await self.scene.update_key('scene', 'task_description', current_description)
        
        await super().data_preparate()

    async def content_worker(self) -> str:
        task = self.scene.data['scene'].get('current_task_data', {})
        current_description = task.get('description', 'Нет описания')

        # Обрезаем длинное описание для предварительного просмотра

        self.content = self.append_variables(task_description=current_description)
        return self.content

    async def update_to_database(self, value: str) -> bool:
        """Обновляем описание в карточке"""
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')

        try:
            await card_events.on_description(new_description=value, card_id=_UUID(str(card_id)))
        except Exception:
            return False

        # Обновляем локальный кэш сцены
        task['description'] = value
        await self.scene.update_key('scene', 'current_task_data', task)
        return True
