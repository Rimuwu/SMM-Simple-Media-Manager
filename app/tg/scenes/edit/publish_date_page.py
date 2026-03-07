from datetime import datetime
from tg.oms.common_pages.date_input_page import DateInputPage
from modules import card_events
from uuid import UUID as _UUID

class PublishDateSetterPage(DateInputPage):

    __page_name__ = 'publish-date-setter'
    __scene_key__ = 'publish_date'
    __next_page__ = 'main-page'
    check_busy_slots = True
    update_to_db = True

    async def update_to_database(self, publish_date: datetime) -> bool:
        """Обновляем дату публикации в карточке"""
        task_id = self.scene.data['scene'].get('task_id')

        try:
            await card_events.on_send_time(new_send_time=publish_date, card_id=_UUID(str(task_id)))
        except Exception:
            return False

        await self.scene.update_key('scene', self.__scene_key__,
                                    publish_date.isoformat()
                                    )
        return True