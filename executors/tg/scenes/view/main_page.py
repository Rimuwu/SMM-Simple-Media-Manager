
from tg.oms import Page
from modules.api_client import get_user_role

class MainPage(Page):
    __page_name__ = 'main'
    
    async def data_preparate(self) -> None:

        telegram_id = self.scene.user_id
        user_role = await get_user_role(telegram_id)

        # Обновляем данные сцены
        await self.scene.update_key('scene', 'user_role', user_role or 'Не определена')

    async def content_worker(self) -> str:
        self.clear_content()

        add_vars = {
            'tasks_count': str(len(self.scene.data['scene'].get('tasks', [])))
        }

        self.content = self.append_variables(**add_vars)
        self.content = self.content.replace('None', '➖')
        
        return self.content