from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import brain_api

class AddCommentPage(TextTypeScene):
    __page_name__ = 'add-comment'
    __scene_key__ = 'comment_text'
    
    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def content_worker(self) -> str:
        """Отображаем введённый текст комментария"""
        comment_text = self.scene.data['scene'].get('comment_text', '')
        
        if comment_text:
            self.content = self.append_variables(comment=comment_text)
        else:
            self.content = self.append_variables(comment='_Введите текст комментария..._')
        
        return self.content

    async def buttons_worker(self):
        buttons = []

        buttons.append({
            "text": "💾 Отправить",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                'send-comment'
            ),
            "ignore_row": True
        })

        buttons.append({
            "text": "🔙 Назад",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                'task-detail'
            ),
            "ignore_row": True
        })
        return buttons

    @Page.on_callback('send-comment')
    async def on_save(self, callback, args):
        comment_text = self.scene.data['scene'].get('comment_text', '')
        
        if not comment_text:
            await callback.answer("❌ Введите текст комментария")
            return

        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            await callback.answer("❌ Задача не найдена")
            return

        card_id = task.get('card_id')
        telegram_id = self.scene.user_id

        # Получаем информацию о пользователе
        from modules.api_client import get_users
        users = await get_users(telegram_id=telegram_id)
        if not users or not isinstance(users, list) or len(users) == 0:
            await callback.answer("❌ Пользователь не найден")
            return

        user = users[0]
        if not isinstance(user, dict):
            await callback.answer("❌ Ошибка данных пользователя")
            return

        user_id = user.get('user_id')

        # Добавляем комментарий через API
        result, status = await brain_api.post(
            "/card/add-comment",
            data={
                "card_id": str(card_id),
                "content": comment_text,
                "author": str(user_id)
            }
        )

        if status == 200:
            await self.scene.update_key('scene', 'comment_text', '')
            await self.scene.update_page('task-detail')
            await callback.answer("✅ Комментарий добавлен")
        else:
            await callback.answer("❌ Ошибка добавления комментария")

    @Page.on_callback('task-detail')
    async def on_back(self, callback, args):
        # Очищаем комментарий при выходе
        await self.scene.update_key('scene', 'comment_text', '')
        await self.scene.update_page('task-detail')
        await self.scene.update_message()
