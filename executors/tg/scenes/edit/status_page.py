from tg.oms import Page
from modules.api_client import update_card, get_cards, get_user_role, get_users, brain_api
from global_modules.classes.enums import CardStatus
from tg.oms.utils import callback_generator
from modules.logs import executors_logger as logger

class StatusSetterPage(Page):
    
    __page_name__ = 'status-setter'
    
    async def can_complete(self) -> bool:
        publish_date = self.scene.data['scene'].get('publish_date')
        content = self.scene.data['scene'].get('content', None)
        status = self.scene.data['scene'].get('status', 'pass_')
        clients = self.scene.data['scene'].get('clients_list', [])

        if publish_date == 'Не указана' and status in ['review']: return False
        if content is None: return False
        if len(clients) == 0: return False

        return True

    async def content_worker(self) -> str:
        self.clear_content()
        self.content = await super().content_worker()
        status = self.scene.data['scene'].get('status', 'pass_')

        if not await self.can_complete():
            if status in ['review']:
                self.content += (
                    "\n\n❌ Дата публикации или контент или каналы не установлены - невозможно завершить задачу."
                )
            else:
                self.content += "\n\n❌ Нельзя отправить на проверку пост без контента или каналов."

        return self.content

    async def buttons_worker(self):
        buttons = await super().buttons_worker()
        
        # Получаем текущий статус задачи
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            cards = await get_cards(card_id=task_id)
            if cards:
                card = cards[0]
                status = card.get('status')
                need_check = card.get('need_check', True)
                
                # Проверяем роль пользователя
                user_role = await get_user_role(self.scene.user_id)
                is_editor_or_admin = user_role in ['admin', 'editor']
                
                # Если статус "Создано" - кнопка "Взять в работу"
                if status == CardStatus.pass_.value:
                    buttons.append({
                        'text': '✏️ Взять в работу',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_edited'
                        )
                    })
                
                # Если статус "В работе"
                elif status == CardStatus.edited.value and await self.can_complete():
                    # Если need_check=False - сразу кнопка завершения
                    if not need_check:
                        buttons.append({
                            'text': '✅ Завершить',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_ready'
                            )
                        })
                    else:
                        # Иначе - отправить на проверку
                        buttons.append({
                            'text': '🔍 Отправить на проверку',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_review'
                            )
                        })

                # Если статус "На проверке" - кнопки для редактора/админа
                elif status == CardStatus.review.value:
                    if await self.can_complete():
                        buttons.append({
                            'text': '✅ Завершить',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_ready'
                            )
                        })
                    buttons.append({
                        'text': '🔙 Вернуть на доработку',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_edited'
                        )
                    })

                # Кнопка "Завершить без отправки" для редактора/админа
                # Доступна если статус "В работе" или "На проверке" и можно завершить
                if is_editor_or_admin and status in [CardStatus.edited.value, CardStatus.review.value]:
                    if await self.can_complete():
                        buttons.append({
                            'text': '🚫 Завершить без отправки',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_ready_no_send'
                            )
                        })
                
                # Кнопка "Вернуть на форум" для админа и исполнителя
                # Доступна если статус "В работе", "На проверке" или "Готова"
                if status in [CardStatus.edited.value, CardStatus.review.value, CardStatus.ready.value]:
                    # Проверяем, является ли пользователь исполнителем этой задачи
                    executor_id = card.get('executor_id')
                    users = await get_users(telegram_id=self.scene.user_id)
                    current_user_id = str(users[0].get('user_id')) if users else None
                    is_executor = current_user_id and str(executor_id) == current_user_id
                    
                    if is_editor_or_admin or is_executor:
                        buttons.append({
                            'text': '📤 Вернуть на форум',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'return_to_forum'
                            ), 
                            'ignore_row': True
                        })

        return buttons

    @Page.on_callback('set_edited')
    async def set_edited_status(self, callback, args):
        """Изменяет статус задачи на "В работе" и устанавливает исполнителя"""
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            # Получаем user_id текущего пользователя
            users = await get_users(telegram_id=self.scene.user_id)
            executor_id = None
            if users:
                executor_id = str(users[0].get('user_id'))
            
            logger.info(f"Пользователь {self.scene.user_id} перевел задачу {task_id} в статус 'В работе' (executor_id={executor_id})")
            
            # Обновляем статус и исполнителя
            await update_card(card_id=task_id, status=CardStatus.edited, executor_id=executor_id)
            await self.scene.update_key('scene', 'status', '✏️ В работе')
            await callback.answer('✅ Статус изменен на "В работе"', show_alert=True)
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_review')
    async def set_review_status(self, callback, args):
        """Изменяет статус задачи на "На проверке" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} отправил задачу {task_id} на проверку")
            await update_card(card_id=task_id, status=CardStatus.review)
            await self.scene.update_key('scene', 'status', '🔍 На проверке')
            await callback.answer('✅ Статус изменен на "На проверке"', show_alert=True)
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_ready')
    async def set_ready_status(self, callback, args):
        """Изменяет статус задачи на "Готова" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} завершил задачу {task_id} (статус 'Готова')")
            await update_card(card_id=task_id, status=CardStatus.ready)
            await self.scene.update_key('scene', 'status', '✅ Готова')
            await callback.answer('✅ Задача завершена!', show_alert=True)
            await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_ready_no_send')
    async def set_ready_no_send_status(self, callback, args):
        """Завершает задачу без отправки в каналы (need_send=False, send_time=None) -> статус sent"""
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} завершил задачу {task_id} без отправки")
            # Устанавливаем need_send=False и сбрасываем send_time
            # Статус будет автоматически изменён на sent в brain-api
            await update_card(
                card_id=task_id, 
                status=CardStatus.ready,
                need_send=False,
                send_time='reset'  # Сбрасываем время отправки
            )
            await self.scene.update_key('scene', 'status', '📤 Отправлена (без публикации)')
            await callback.answer('✅ Задача завершена без отправки!')
            await self.scene.__bot__.send_message(
                chat_id=self.scene.user_id,
                text="Задача завершена без отправки."
            )
            # await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('return_to_forum')
    async def return_to_forum_status(self, callback, args):
        """Возвращает задачу на форум: сбрасывает исполнителя, статус на pass_, пересоздаёт сообщение форума"""
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} возвращает задачу {task_id} на форум")
            
            # Вызываем специальный эндпоинт для возврата на форум
            res, status = await brain_api.post(
                '/card/return-to-forum',
                data={'card_id': task_id}
            )
            
            if status == 200:
                await self.scene.update_key('scene', 'status', '⏳ Создано')
                await callback.answer('✅ Задача возвращена на форум!', show_alert=True)
                # Закрываем сцену редактирования, так как задача больше не у исполнителя
                await self.scene.end()
            else:
                error_msg = res.get('detail', 'Неизвестная ошибка') if isinstance(res, dict) else str(res)
                await callback.answer(f'❌ Ошибка: {error_msg}', show_alert=True)
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
