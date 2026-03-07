from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.brain_client import brain_client
from global_modules.classes.enums import CardStatus
from global_modules.brain_client import add_editor_note

class EditorNotesPage(Page):
    
    __page_name__ = 'editor-notes'
    _card_cache: dict | None = None
    
    async def data_preparate(self):
        """Загружаем комментарии и форматируем их"""
        task_id = self.scene.data['scene'].get('task_id')
        self._card_cache = None
        
        if task_id:
            cards = await brain_client.get_cards(card_id=task_id)
            if cards:
                card = cards[0]
                self._card_cache = card
                editor_notes = card.get('editor_notes', [])

                if editor_notes:
                    # Загружаем всех пользователей единым запросом
                    all_users = await brain_client.get_users()
                    users_dict = {str(u['user_id']): u for u in all_users} if all_users else {}

                    # Форматируем комментарии с учетом лимита символов
                    formatted_notes = []
                    total_length = 0
                    max_length = 800
                    displayed_count = 0
                    
                    # Идем от последнего к первому (новые комментарии первыми)
                    for i, note in enumerate(reversed(editor_notes), 1):
                        content = note.get('content', 'Пусто')
                        author_id = str(note.get('author', ''))
                        is_customer = note.get('is_customer', False)
                        
                        author_name = 'Неизвестный'
                        if author_id:
                            user_data = users_dict.get(author_id)
                            if user_data:
                                author_name = await get_display_name(
                                        user_data['telegram_id'], 
                                        self.scene.__bot__,
                                        short=True
                                    )

                        # Формируем текст комментария с пометкой для заказчика
                        if is_customer:
                            note_text = f"📋 {len(editor_notes) - i + 1}. *Заказчик* ({author_name}):\n`{content}`"
                        else:
                            note_text = f"💬 {len(editor_notes) - i + 1}. от {author_name}:\n`{content}`"
                        note_length = len(note_text) + 2  # +2 для "\n\n"
                        
                        # Проверяем, не превысим ли лимит
                        if total_length + note_length <= max_length:
                            formatted_notes.insert(0, note_text)  # Вставляем в начало для правильного порядка
                            total_length += note_length
                            displayed_count += 1
                        else:
                            break
                    
                    # Если показаны не все комментарии, добавляем информацию об этом
                    if displayed_count < len(editor_notes):
                        hidden_count = len(editor_notes) - displayed_count
                        formatted_notes.insert(0, f"_...еще {hidden_count} комментари{'й' if hidden_count > 4 else 'ев'}_\n")
                    
                    notes_text = "\n\n".join(formatted_notes)
                    await self.scene.update_key('scene', 'formatted_notes', notes_text)
                    await self.scene.update_key('scene', 'has_notes', True)
                else:
                    await self.scene.update_key('scene', 'formatted_notes', 'Комментариев пока нет')
                    await self.scene.update_key('scene', 'has_notes', False)
    
    async def buttons_worker(self):
        """Формируем кнопки"""
        buttons = []
        
        # Используем кеш из data_preparate
        card = self._card_cache
        if card:
            status = card.get('status')
            # Если статус "На проверке", добавляем кнопку "Вернуть в работу"
            if status == CardStatus.review.value:
                    buttons.append({
                        'text': '🔙 Вернуть в работу',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'return_to_work'
                        ),
                        'ignore_row': True
                    })
        
        # Кнопка назад
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_to_main'
            ),
            'ignore_row': True
        })
        
        return buttons
    
    @Page.on_callback('return_to_work')
    async def return_to_work(self, callback, args):
        """Возвращает задачу в работу"""
        task_id = self.scene.data['scene'].get('task_id')

        if task_id:
            user_role = await brain_client.get_user_role(self.scene.user_id)

            who_changed = 'executor' if user_role == 'copywriter' else 'admin'
            await brain_client.change_card_status(
                card_id=task_id,
                status=CardStatus.edited,
                who_changed=who_changed
            )
            
            # Обновляем отображение статуса
            await self.scene.update_key('scene', 'status', '✏️ В работе')
            
            await callback.answer('✅ Задача возвращена в работу', show_alert=True)
            
            # Возвращаемся на главную страницу
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)

    @Page.on_text('all')
    async def handle_comment_text(self, message):
        """Обработка текстового сообщения - добавление комментария"""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Создаем inline кнопку для удаления сообщения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_message")]
        ])

        text = message.text

        if not text or len(text) < 5:
            await message.answer('❌ Комментарий слишком короткий. Минимум 5 символов.',
                                 reply_markup=keyboard)
            return

        if len(text) > 256:
            await message.answer('❌ Комментарий слишком длинный. Максимум 256 символа.', 
                                 reply_markup=keyboard)
            return

        task_id = self.scene.data['scene'].get('task_id')

        if task_id:
            # Получаем user_id текущего пользователя
            telegram_id = self.scene.user_id
            
            # Получаем user_id из базы по telegram_id
            users = await brain_client.get_users(telegram_id=telegram_id)
            
            if not users:
                await message.answer('❌ Пользователь не найден в системе')
                return
            
            author_user_id = str(users[0]['user_id'])
            
            # Добавляем комментарий
            result = await add_editor_note(task_id, text, author_user_id)

            if result:
                # Перезагружаем страницу для обновления списка комментариев
                await self.scene.update_page('editor-notes')
            else:
                await message.answer('❌ Ошибка при добавлении комментария')
        else:
            await message.answer('❌ Ошибка: задача не найдена')
    
    @Page.on_callback('back_to_main')
    async def back_to_main(self, callback, args):
        """Возврат на главную страницу"""
        await self.scene.update_page('main-page')

