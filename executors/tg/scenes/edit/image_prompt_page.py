"""
Страница для отправки ТЗ дизайнерам
"""
from datetime import datetime
from modules.utils import get_display_name
from tg.oms import Page
from tg.oms.utils import callback_generator
from global_modules.brain_client import brain_client
from modules.constants import SETTINGS


class ImagePromptPage(Page):
    
    __page_name__ = 'image-prompt'
    
    async def data_preparate(self):
        """Подготовка данных"""
        card = await self.scene.get_card_data()
        if not card:
            return
        
        # Загружаем текущий image_prompt
        current_prompt = card.get('image_prompt') or ''
        await self.scene.update_key('scene', 'image_prompt', current_prompt)
        
        # Проверяем, отправлено ли уже сообщение дизайнерам
        prompt_message = card.get('prompt_message')
        await self.scene.update_key('scene', 'prompt_sent', prompt_message is not None)
    
    async def content_worker(self) -> str:
        """Формируем контент страницы"""
        card = await self.scene.get_card_data()
        if not card:
            return "❌ Задача не найдена"
        
        image_prompt = self.scene.data['scene'].get('image_prompt') or 'Не указано'
        prompt_sent = self.scene.data['scene'].get('prompt_sent', False)
        
        # Проверяем флаг ошибки ввода
        not_handled = self.scene.data['scene'].get('not_handled')
        error_text = ""
        if not_handled:
            error_text = "⚠️ *Введите текст описания картинки!*\n\n"
            await self.scene.update_key('scene', 'not_handled', False)
        
        status_text = "✅ Отправлено дизайнерам" if prompt_sent else "⏳ Ожидает отправки"
        
        return self.append_variables(
            error_text=error_text,
            image_prompt=image_prompt,
            status=status_text
        )
    
    async def buttons_worker(self) -> list[dict]:
        """Формируем кнопки"""
        buttons = []
        
        prompt_sent = self.scene.data['scene'].get('prompt_sent', False)
        image_prompt = self.scene.data['scene'].get('image_prompt')
        
        if image_prompt and image_prompt.strip():
            if not prompt_sent:
                buttons.append({
                    'text': '📤 Отправить дизайнерам',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'send_to_designers'
                    ),
                    'ignore_row': True
                })
            else:
                buttons.append({
                    'text': '🔄 Отправить повторно',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'send_to_designers'
                    ),
                    'ignore_row': True
                })
        
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'main-page'
            ),
            'ignore_row': True
        })
        
        return buttons
    
    @Page.on_text('str')
    async def handle_text(self, message, value: str):
        """Обработка ввода текста"""
        text = value.strip()
        
        if len(text) < 5:
            await self.scene.update_key('scene', 'not_handled', True)
            await self.scene.update_message()
            return
        
        # Ограничение в 1024 символа
        if len(text) > 1024:
            text = text[:1024]
        
        # Сохраняем в сцену
        await self.scene.update_key('scene', 'image_prompt', text)
        
        # Сохраняем в БД
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            await brain_client.update_card(task_id, image_prompt=text)
        
        await self.scene.update_message()
    
    @Page.on_callback('send_to_designers')
    async def send_to_designers(self, callback, args):
        """Отправка сообщения дизайнерам"""
        card = await self.scene.get_card_data()
        if not card:
            await callback.answer("❌ Задача не найдена", show_alert=True)
            return
        
        image_prompt = self.scene.data['scene'].get('image_prompt')
        if not image_prompt or not image_prompt.strip():
            await callback.answer("❌ Сначала введите описание картинки", show_alert=True)
            return
        
        # Получаем данные для сообщения
        design_group = SETTINGS.get('design_group')
        if not design_group:
            await callback.answer("❌ Группа дизайнеров не настроена", show_alert=True)
            return
        
        # Форматируем дедлайн
        deadline = card.get('deadline')
        deadline_str = "Не указан"
        if deadline:
            try:
                dt = datetime.fromisoformat(deadline)
                deadline_str = dt.strftime('%d.%m.%Y %H:%M')
            except:
                pass
        
        # Получаем имена исполнителя и заказчика
        kaiten_users = await brain_client.get_kaiten_users_dict()

        executor_name = "Не назначен"
        if card.get('executor_id'):
            executor_users = await brain_client.get_users(user_id=card['executor_id'])
            if executor_users and isinstance(executor_users[0], dict):
                executor_name = await get_display_name(
                    executor_users[0]['telegram_id'], 
                    kaiten_users, self.scene.__bot__, 
                    executor_users[0].get('tasker_id')
                )

        customer_name = "Не указан"
        if card.get('customer_id'):
            customer_users = await brain_client.get_users(user_id=card['customer_id'])
            if customer_users and isinstance(customer_users[0], dict):
                customer_name = await get_display_name(
                    customer_users[0]['telegram_id'], 
                    kaiten_users, self.scene.__bot__, 
                    customer_users[0].get('tasker_id')
                )

        # Формируем сообщение
        message_text = (
            f"🤖 _Это сообщение создано автоматически._\n\n"
            "#Задача\n"
            f"⏰ *Дедлайн:* {deadline_str}\n"
            f"👤 *Исполнитель:* {executor_name}\n"
            f"👤 *Заказчик:* {customer_name}\n"
            f"🖼 *ТЗ для картинки:* {image_prompt}\n\n"
            f"📸 *Ответьте на это сообщение фотографией*, "
            f"чтобы прикрепить её к задаче."
        )
        
        try:
            # Удаляем старое сообщение если есть
            old_message_id = card.get('prompt_message')
            if old_message_id:
                try:
                    await self.scene.__bot__.delete_message(
                        chat_id=design_group,
                        message_id=old_message_id
                    )
                except:
                    pass
            
            # Отправляем сообщение
            sent_message = await self.scene.__bot__.send_message(
                chat_id=design_group,
                text=message_text,
                parse_mode="Markdown"
            )
            
            # Сохраняем ID сообщения
            task_id = self.scene.data['scene'].get('task_id')
            await brain_client.update_card(task_id, prompt_message=sent_message.message_id)
            
            await self.scene.update_key('scene', 'prompt_sent', True)
            await callback.answer("✅ Сообщение отправлено дизайнерам", show_alert=True)
            await self.scene.update_message()
            
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)
    
    @Page.on_callback('main-page')
    async def go_back(self, callback, args):
        """Возврат на главную"""
        await self.scene.update_page('main-page')
