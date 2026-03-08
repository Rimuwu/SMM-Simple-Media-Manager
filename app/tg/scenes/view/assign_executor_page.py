from modules.utils import get_user_display_name
from tg.oms.common_pages import UserSelectorPage
from modules.card import card_events
from uuid import UUID as _UUID
from modules.enums import CardStatus

class AssignExecutorPage(UserSelectorPage):

    __page_name__ = 'assign-executor'
    __scene_key__ = 'executor_id'
    __next_page__ = 'task-detail'

    update_to_db = True
    allow_reset = True
    filter_department = 'smm'  # Фильтруем только пользователей из SMM департамента
    filter_roles = ['copywriter', 'editor', 'admin']

    async def data_preparate(self):
        """Подгружаем текущего исполнителя из данных задачи"""
        task = self.scene.data['scene'].get('current_task_data')

        if task:
            selected_value = task.get('executor_id')

            await self.scene.update_key(
                'scene', 
                self.scene_key, selected_value)
            await self.scene.update_key(
                self.__page_name__, 
                self.scene_key, selected_value)

        await super().data_preparate()

    async def update_to_database(self, user_id) -> bool:
        """Обновляем исполнителя в карточке"""

        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            return False

        card_id = task.get('card_id')
        current_status = task.get('status')

        new_executor_id = _UUID(str(user_id)) if user_id else None

        try:
            await card_events.on_executor(new_executor_id=new_executor_id, card_id=_UUID(str(card_id)))
        except Exception:
            return False

        # Обновляем локальный кэш сцены
        task['executor_id'] = user_id

        # Если статус был pass_ и назначили исполнителя — отражаем смену статуса локально
        if user_id and (current_status == CardStatus.pass_.value or current_status == CardStatus.pass_):
            task['status'] = CardStatus.edited.value

        # Обновляем информацию об исполнителе для отображения
        if user_id:
            selected_user = next(
                (u for u in self.users_data if isinstance(u, dict) and str(u.get('user_id', '')) == str(user_id)),
                None
            )
            if selected_user and isinstance(selected_user, dict):
                telegram_id = selected_user.get('telegram_id')
                task['executor'] = {
                    'user_id': str(user_id),
                    'telegram_id': telegram_id,
                    'full_name': get_user_display_name(selected_user)
                }
        else:
            task['executor'] = None

        await self.scene.update_key('scene', 'current_task_data', task)
        return True
