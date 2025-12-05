from tg.oms.common_pages import UserSelectorPage
from modules.api_client import update_card
from modules.api_client import brain_api

class AssignExecutorPage(UserSelectorPage):

    __page_name__ = 'assign-executor'
    __scene_key__ = 'executor_id'
    __next_page__ = 'task-detail'
    
    scene_key = 'executor_id'
    next_page = 'task-detail'
    
    update_to_db = True
    allow_reset = True
    filter_department = 'smm'  # Фильтруем только пользователей из SMM департамента
    filter_roles = ['copywriter', 'editor', 'admin']

    async def data_preparate(self):
        """Подгружаем текущего исполнителя из данных задачи"""
        task = self.scene.data['scene'].get('current_task_data')
        if task:
            executor_id = task.get('executor_id')
            if executor_id:
                await self.scene.update_key('scene', 'executor_id', str(executor_id))
        
        await super().data_preparate()

    async def update_to_database(self, user_id) -> bool:
        """Обновляем исполнителя в карточке"""
        print("Updating executor to database:", user_id)
        
        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')

        if user_id == None:
            response, status = await brain_api.get(f"/card/delete-executor/{card_id}")
            success = (status == 200)

        else:
            # Обновляем карточку
            result = await update_card(
                card_id=card_id,
                executor_id=user_id
            )
            success = result is not None
            print("Update executor response:", result)

        if success:
            # Обновляем данные задачи
            task['executor_id'] = user_id

            # Обновляем информацию об исполнителе для отображения
            if user_id:
                selected_user = next(
                    (u for u in self.users_data if isinstance(u, dict) and str(u.get('user_id', '')) == str(user_id)), 
                    None
                )
                if selected_user and isinstance(selected_user, dict):
                    # Получаем отображаемое имя пользователя
                    display_name = await self.get_display_name(
                        selected_user,
                        self.kaiten_users,
                        self.scene.__bot__
                    )
                    
                    telegram_id = selected_user.get('telegram_id')
                    tasker_id = selected_user.get('tasker_id')
                    
                    task['executor'] = {
                        'user_id': str(user_id),
                        'telegram_id': telegram_id,
                        'tasker_id': tasker_id,
                        'full_name': display_name
                    }
            else:
                task['executor'] = None

            await self.scene.update_key('scene', 'current_task_data', task)
            return True

        return False
