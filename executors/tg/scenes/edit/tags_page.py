from tg.oms.common_pages import TagsSelectorPage
from modules.api_client import update_card


class TagsSetterPage(TagsSelectorPage):

    __page_name__ = 'tags-setter'
    __scene_key__ = 'tags_list'
    
    update_to_db = True
    
    async def update_to_database(self, tags_list: list) -> bool:
        """Обновляем теги в карточке"""
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            return False
        
        # Обновляем карточку
        success = await update_card(
            card_id=task_id,
            tags=tags_list
        )
        
        return success is not None
