from tg.oms.models.text_page import TextTypeScene
from modules.api_client import brain_api


class ChangeNamePage(TextTypeScene):
    
    __page_name__ = 'change-name'
    __scene_key__ = 'task_name'
    __next_page__ = 'task-detail'
    
    update_to_db = True

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
        old_name = task.get('name')
        
        # Обновляем название в карточке
        result, status = await brain_api.post(
            "/card/update",
            data={
                "card_id": str(card_id),
                "name": value,
                "notify_executor": True,
                "change_type": "name",
                "old_value": old_name,
                "new_value": value
            }
        )

        if status == 200:
            # Обновляем данные задачи
            task['name'] = value
            await self.scene.update_key('scene', 'current_task_data', task)
            return True
        
        return False
