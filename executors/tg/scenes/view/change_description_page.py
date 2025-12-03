from tg.oms.models.text_page import TextTypeScene
from modules.api_client import brain_api


class ChangeDescriptionPage(TextTypeScene):
    
    __page_name__ = 'change-description'
    __scene_key__ = 'task_description'
    __next_page__ = 'task-detail'
    
    update_to_db = True

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
        result, status = await brain_api.post(
            "/card/update",
            data={
                "card_id": str(card_id),
                "description": value,
                "notify_executor": True,
                "change_type": "description",
                "old_value": old_description,
                "new_value": value
            }
        )

        if status == 200:
            # Обновляем данные задачи
            task['description'] = value
            await self.scene.update_key('scene', 'current_task_data', task)
            return True
        
        return False
