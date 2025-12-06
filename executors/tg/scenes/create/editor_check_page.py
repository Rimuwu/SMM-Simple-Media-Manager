from tg.oms import Page
from modules.api_client import get_user_role
from tg.oms.utils import callback_generator
from modules.logs import executors_logger as logger


class EditorCheckPage(Page):
    """
    Страница настройки проверки редактором при создании задачи.
    Доступна только для администраторов.
    """
    
    __page_name__ = 'editor-check'
    
    async def content_worker(self) -> str:
        self.clear_content()
        
        editor_check = self.scene.data['scene'].get('editor_check', True)
        status_text = "✅ Включена" if editor_check else "❌ Отключена"
        
        self.content = f"⚙️ **Проверка редактором**\n\nТекущий статус: {status_text}\n\nЕсли проверка отключена, копирайтер сможет сразу завершить задачу без этапа проверки редактором."
        
        return self.content

    async def buttons_worker(self):
        buttons = []
        
        editor_check = self.scene.data['scene'].get('editor_check', True)
        
        if editor_check:
            buttons.append({
                'text': '❌ Отключить проверку',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'disable_check'
                )
            })
        else:
            buttons.append({
                'text': '✅ Включить проверку',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'enable_check'
                )
            })

        return buttons

    @Page.on_callback('enable_check')
    async def enable_check(self, callback, args):
        """Включает проверку редактором"""
        logger.info(f"Админ {self.scene.user_id} включил проверку редактором при создании задачи")
        await self.scene.update_key('scene', 'editor_check', True)
        await callback.answer('✅ Проверка редактором включена', show_alert=True)
        await self.scene.update_page('editor-check')
    
    @Page.on_callback('disable_check')
    async def disable_check(self, callback, args):
        """Отключает проверку редактором"""
        logger.info(f"Админ {self.scene.user_id} отключил проверку редактором при создании задачи")
        await self.scene.update_key('scene', 'editor_check', False)
        await callback.answer('❌ Проверка редактором отключена', show_alert=True)
        await self.scene.update_page('editor-check')
