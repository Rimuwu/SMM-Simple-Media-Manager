from datetime import datetime
from tg.oms.common_pages.date_input_page import DateInputPage
from global_modules.brain_client import brain_client

class PublishDateSetterPage(DateInputPage):

    __page_name__ = 'publish-date-setter'
    __scene_key__ = 'publish_date'
    __next_page__ = 'main-page'
    check_busy_slots = True
    update_to_db = True

    async def update_to_database(self, publish_date: datetime) -> bool:
        """Обновляем дату публикации в карточке"""
        task_id = self.scene.data['scene'].get('task_id')

        # Обновляем дату публикации в карточке
        res = await brain_client.update_card(
            card_id=task_id,
            send_time=publish_date.isoformat()
        )

        if res is not None:
            # Обновляем данные задачи
            await self.scene.update_key('scene', self.__scene_key__, 
                                        publish_date.isoformat()
                                        )
            return True

        return False