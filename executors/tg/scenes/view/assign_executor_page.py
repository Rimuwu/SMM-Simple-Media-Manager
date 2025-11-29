from tg.oms.common_pages import UserSelectorPage
from modules.api_client import update_card
from modules.api_client import brain_api

class AssignExecutorPage(UserSelectorPage):

    __page_name__ = 'assign-executor'
    __scene_key__ = 'executor_id'
    __next_page__ = 'task-detail'

    update_to_db = True
    allow_reset = True

    # async def content_worker(self) -> str:
    #     task = self.scene.data['scene'].get('current_task_data', {})

    #     users, status = await brain_api.get('/user/get')
    #     all_users = users if status == 200 and users else []

    #     kaiten_users = {}
    #     k_users, k_status = await brain_api.get('/kaiten/get-users', params={'only_virtual': 1})
    #     if k_status == 200 and k_users:
    #         kaiten_users = {u['id']: u['full_name'] for u in k_users}

    #     executor_id = task.get('executor_id')
    #     executor_name = 'Не указан'
    #     if executor_id:
    #         user_data = next((u for u in all_users if str(u['user_id']) == str(executor_id)), None)
    #         if user_data:
    #             executor_name = await UserSelectorPage.get_display_name(
    #                 user_data, 
    #                 kaiten_users, 
    #                 self.scene.__bot__
    #             )

    #     self.content = self.append_variables(executor=executor_name)
    #     return self.content
    
    async def data_preparate(self):
        self.executor = '234'
        
        return await super().data_preparate()

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
            success = await update_card(
                card_id=card_id,
                executor_id=user_id
            )
            print("Update executor response:", success)

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
