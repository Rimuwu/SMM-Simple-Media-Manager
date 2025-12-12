from global_modules import brain_client
from tg.oms.common_pages.update_text_page import UpdateTextPage
from modules.api_client import brain_api
from global_modules.classes.enums import ChangeType


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
        if len(current_description) > 200:
            current_description = current_description[:200] + "..."
            
        self.content = self.append_variables(task_description=current_description)
        return self.content

    async def update_to_database(self, value: str) -> bool:
        """Обновляем описание в карточке"""
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')
        old_description = task.get('description')
        
        # Обновляем описание в карточке
        res = await brain_client.update_card(
            card_id=card_id,
            description=value
        )

        if res is not None:
            # Обновляем данные задачи
            task['description'] = value
            await self.scene.update_key('scene', 'current_task_data', task)
            return True
        
        return False
