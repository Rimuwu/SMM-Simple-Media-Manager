from tg.oms.models.text_page import TextTypeScene
from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.api_client import brain_api, get_cards, get_users, get_kaiten_users_dict
from tg.oms.common_pages import UserSelectorPage

class AddCommentPage(TextTypeScene):
    __page_name__ = 'add-comment'
    __scene_key__ = 'comment_text'
    
    def __after_init__(self):
        super().__after_init__()
        self.next_page = ''

    async def data_preparate(self):
        """Загружаем комментарии и форматируем их"""
        task = self.scene.data['scene'].get('current_task_data')
        
        if task:
            card_id = task.get('card_id')
            cards = await get_cards(card_id=card_id)
            
            if cards:
                card = cards[0]
                editor_notes = card.get('editor_notes', [])

                if editor_notes:
                    # Получаем всех пользователей для отображения имен
                    users = await get_users()
                    users_dict = {str(u['user_id']): u for u in users} if users else {}
                    kaiten_users = await get_kaiten_users_dict()
                    
                    # Форматируем комментарии с учетом лимита символов
                    formatted_notes = []
                    total_length = 0
                    max_length = 600
                    displayed_count = 0
                    
                    # Идем от последнего к первому (новые комментарии первыми)
                    for i, note in enumerate(reversed(editor_notes), 1):
                        content = note.get('content', 'Пусто')
                        author_id = str(note.get('author', ''))
                        is_customer = note.get('is_customer', False)
                        
                        author_name = 'Неизвестный'
                        if author_id:
                            author_users = await get_users(user_id=author_id)
                            if author_users:
                                user_data = author_users[0]
                                author_name = await UserSelectorPage.get_display_name(
                                    user_data, kaiten_users, self.scene.__bot__
                                )

                        # Формируем текст комментария с пометкой для заказчика
                        if is_customer:
                            note_text = f"📋 {len(editor_notes) - i + 1}. *Заказчик* ({author_name}):\n`{content}`"
                        else:
                            note_text = f"💬 {len(editor_notes) - i + 1}. от {author_name}:\n`{content}`"
                        
                        note_length = len(note_text) + 2  # +2 для "\n\n"
                        
                        # Проверяем, не превысим ли лимит
                        if total_length + note_length <= max_length:
                            formatted_notes.insert(0, note_text)
                            total_length += note_length
                            displayed_count += 1
                        else:
                            break
                    
                    # Если показаны не все комментарии
                    if displayed_count < len(editor_notes):
                        hidden_count = len(editor_notes) - displayed_count
                        formatted_notes.insert(0, f"_...еще {hidden_count} комментари{'й' if hidden_count > 4 else 'ев'}_\n")
                    
                    notes_text = "\n\n".join(formatted_notes)
                    await self.scene.update_key('scene', 'comments_history', notes_text)
                else:
                    await self.scene.update_key('scene', 'comments_history', '_Комментариев пока нет_')
            else:
                await self.scene.update_key('scene', 'comments_history', '_Комментариев пока нет_')
        else:
            await self.scene.update_key('scene', 'comments_history', '_Комментариев пока нет_')

    async def content_worker(self) -> str:
        """Отображаем историю комментариев и введённый текст"""
        comment_text = self.scene.data['scene'].get('comment_text', '')
        comments_history = self.scene.data['scene'].get('comments_history', '_Комментариев пока нет_')
        
        if comment_text:
            self.content = self.append_variables(
                comments_history=comments_history,
                comment=comment_text
            )
        else:
            self.content = self.append_variables(
                comments_history=comments_history,
                comment='_Введите текст комментария..._'
            )
        
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
