from tg.oms.common_pages import TagsSelectorPage
from models.Card import Card
from uuid import UUID as _UUID


class TagsSetterPage(TagsSelectorPage):

    __page_name__ = 'tags-setter'
    __scene_key__ = 'tags_list'
    update_to_db = True
    
    __max_on_page__: int = 9

    async def update_to_database(self, tags_list: list) -> bool:
        """Обновляем теги в карточке при выходе со страницы"""
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return False

        card = await Card.get_by_id(_UUID(str(task_id)))
        if card:
            await card.update(tags=tags_list)
            return True
        return False
