from tg.oms import Page
from modules.exec.brain_client import brain_client
from modules.enums import CardStatus
from tg.oms.utils import callback_generator
from modules.logs import logger
from datetime import datetime, timedelta

class StatusSetterPage(Page):
    
    __page_name__ = 'status-setter'
    _card_cache: dict | None = None

    async def data_preparate(self):
        """Загружаем и кешируем данные карточки один раз за цикл рендера"""
        task_id = self.scene.data['scene'].get('task_id')
        self._card_cache = None
        if task_id:
            cards = await brain_client.get_cards(card_id=task_id)
            self._card_cache = cards[0] if cards else None
    async def can_complete(self) -> bool:
        publish_date = self.scene.data['scene'].get('publish_date')
        content = self.scene.data['scene'].get('content', None)
        status = self.scene.data['scene'].get('status', 'pass_')
        clients = self.scene.data['scene'].get('clients_list', [])

        if publish_date == 'Не указана' and status in ['review']: return False
        if not content: return False
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

        # Дополнительные предупреждения: время отправки, фото, теги
        warnings = []
        card = self._card_cache
        if card:
                send_time = card.get('send_time')
                if send_time:
                    try:
                        st = datetime.fromisoformat(send_time)
                        now = datetime.now()
                        if st < now:
                            warnings.append('⏰ Время отправки уже прошло.')
                        elif (st - now) < timedelta(minutes=5):
                            warnings.append('⏳ Время отправки менее чем через 5 минут.')
                    except Exception:
                        # невалидный формат — игнорируем
                        pass

                # Проверка наличия фото (post_images)
                post_images = card.get('post_images') or []
                if not post_images:
                    warnings.append('🖼 Нет установленных изображений для поста.')

                # Проверка наличия тегов
                tags = card.get('tags') or []
                if not tags:
                    warnings.append('🏷 Нет установленных хештегов.')

        if warnings:
            self.content += '\n\n⚠️ *Предупреждения при завершении:*\n'
            for w in warnings:
                self.content += f'- {w}\n'

            self.content += '\nПри выборе "🚫 Завершить без отправки" задача будет помечена как завершённая и НЕ будет отправляться в каналы; после этого её нельзя будет автоматически опубликовать.'

        return self.content

    async def buttons_worker(self):
        buttons = await super().buttons_worker()

        card = self._card_cache
        if not card:
            return buttons

        status = card.get('status')
        need_check = card.get('need_check', True)
        executor_id = card.get('executor_id')

        # Получаем информацию о пользователе
        user_role = await brain_client.get_user_role(self.scene.user_id)
        users = await brain_client.get_users(telegram_id=self.scene.user_id)
        current_user_id = str(users[0].get('user_id')) if users else None
        
        # Флаги ролей
        is_admin = user_role == 'admin'
        is_editor = user_role == 'editor'
        is_copywriter = user_role == 'copywriter'
        is_editor_or_admin = is_admin or is_editor
        is_executor = current_user_id and str(executor_id) == current_user_id
        
        can_complete = await self.can_complete()

        if status == CardStatus.pass_.value:
            # Любой может взять в работу
            buttons.append({
                'text': '✏️ Взять в работу',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'set_edited',
                    'set_executor'
                )
            })

        elif status == CardStatus.edited.value:
            if can_complete:
                # Если проверка не нужна (need_check=False)
                if not need_check:
                    buttons.append({
                        'text': '✅ Завершить',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_ready'
                        )
                    })
                    buttons.append({
                        'text': '🚫 Завершить без отправки',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_ready_no_send',
                        ),
                        'ignore_row': True
                    })
                # Если нужна проверка
                else:
                    # Копирайтер и админ могут отправить на проверку
                    if is_copywriter or is_admin:
                        buttons.append({
                            'text': '🔍 Отправить на проверку',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_review'
                            )
                        })

                    # Редактор/админ могут сразу завершить без отправки
                    if is_editor_or_admin:
                        buttons.append({
                            'text': '🚫 Завершить без отправки',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_ready_no_send',
                            ),
                            'next_line': True
                        })
                        buttons.append({
                            'text': '✅ Завершить',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'set_ready'
                            )
                        })

            # Вернуть на форум (исполнитель или админ)
            if is_executor or is_admin:
                buttons.append({
                    'text': '📤 Вернуть на форум',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'return_to_forum'
                    ), 
                    'ignore_row': True
                })

        elif status == CardStatus.review.value:
            # Редактор/админ могут завершить или вернуть
            if can_complete:
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
                    'set_edited',
                    'no_set_executor'
                )
            })
            
            # Редактор/админ могут завершить без отправки
            if is_editor_or_admin and can_complete:
                buttons.append({
                    'text': '🚫 Завершить без отправки',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'set_ready_no_send',
                    ),
                    'ignore_row': True
                })
            
            # Вернуть на форум (исполнитель или админ)
            if is_executor or is_admin:
                buttons.append({
                    'text': '📤 Вернуть на форум',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'return_to_forum'
                    ), 
                    'ignore_row': True
                })

        elif status == CardStatus.ready.value:
            # Вернуть на форум (исполнитель или админ)
            if is_executor or is_admin:
                buttons.append({
                    'text': '🔙 Вернуть на доработку',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'set_edited',
                        'no_set_executor'
                    )
                })

        return buttons

    @Page.on_callback('set_edited')
    async def set_edited_status(self, callback, args: list):
        """Изменяет статус задачи на "В работе" и устанавливает исполнителя"""
        task_id = self.scene.data['scene'].get('task_id')
        set_executor = args[1] == 'set_executor'

        if task_id:
            # Получаем роль пользователя
            user_role = await brain_client.get_user_role(self.scene.user_id)
            who_changed = 'executor' if user_role == 'copywriter' else 'admin'

            # Получаем user_id текущего пользователя
            users = await brain_client.get_users(telegram_id=self.scene.user_id)
            executor_id = None
            if users:
                executor_id = str(users[0].get('user_id'))

            logger.info(f"Пользователь {self.scene.user_id} перевел задачу {task_id} в статус 'В работе' (executor_id={executor_id})")

            # Обновляем статус
            await brain_client.change_card_status(
                card_id=task_id,
                status=CardStatus.edited,
                who_changed=who_changed
            )

            # Устанавливаем исполнителя отдельно
            if set_executor:
                await brain_client.update_card(card_id=task_id, executor_id=executor_id)

            await self.scene.update_key(
                'scene', 'status', '✏️ В работе')
            await callback.answer('✅ Статус изменен на "В работе"', show_alert=True)
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_review')
    async def set_review_status(self, callback, args):
        """Изменяет статус задачи на "На проверке" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} отправил задачу {task_id} на проверку")
            await brain_client.change_card_status(
                card_id=task_id,
                status=CardStatus.review,
                who_changed='executor'
            )
            
            await self.scene.update_key(
                'scene', 'status', '🔍 На проверке')
            await callback.answer(
                '✅ Статус изменен на "На проверке"', show_alert=True)
            await self.scene.update_message()
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_ready')
    async def set_ready_status(self, callback, args):
        """Изменяет статус задачи на "Готова" """
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            logger.info(f"Пользователь {self.scene.user_id} завершил задачу {task_id} (статус 'Готова')")
            
            # Получаем роль пользователя
            user_role = await brain_client.get_user_role(self.scene.user_id)
            who_changed = 'executor' if user_role == 'copywriter' else 'admin'
            
            await brain_client.change_card_status(
                card_id=task_id,
                status=CardStatus.ready,
                who_changed=who_changed
            )
            
            await self.scene.update_key('scene', 'status', '✅ Готова')
            await callback.answer('✅ Задача завершена!', show_alert=True)
            # await self.scene.update_page('main-page')
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)
    
    @Page.on_callback('set_ready_no_send')
    async def set_ready_no_send_status(self, callback, args):
        """Завершает задачу без отправки в каналы (need_send=False, send_time=None) -> статус sent"""
        task_id = self.scene.data['scene'].get('task_id')
        
        if task_id:
            # Предупреждение пользователю (информируем перед действием)
            await callback.answer(
                '⚠️ Вы собираетесь завершить задачу без отправки — задача будет помечена как завершённая и НЕ будет отправлена в каналы.\n\nПродолжить?',
                show_alert=True
            )

            logger.info(f"Пользователь {self.scene.user_id} завершил задачу {task_id} без отправки")
            
            # Получаем роль пользователя
            user_role = await brain_client.get_user_role(self.scene.user_id)
            who_changed = 'executor' if user_role == 'copywriter' else 'admin'
            
            # Устанавливаем need_send=False и сбрасываем send_time
            await brain_client.update_card(
                card_id=task_id,
                need_send=False,
                send_time='reset'  # Сбрасываем время отправки
            )
            
            # Меняем статус на ready (закрытая без отправки)
            await brain_client.change_card_status(
                card_id=task_id,
                status=CardStatus.ready,
                who_changed=who_changed
            )
            
            await self.scene.update_key('scene', 'status', '📤 Отправлена (без публикации)')
            await callback.answer('✅ Задача завершена без отправки!')
            await self.scene.__bot__.send_message(
                chat_id=self.scene.user_id,
                text="Задача завершена без отправки. Она больше не будет отправляться и не будет доступна для публикации."
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
            user_role = await brain_client.get_user_role(self.scene.user_id)
            who = 'executor' if user_role == 'copywriter' else 'admin'
            
            res = await brain_client.change_card_status(
                card_id=task_id,
                status=CardStatus.pass_,
                who_changed=who
            )

            if res:
                await self.scene.update_key('scene', 'status', '⏳ Создано')
                await callback.answer('✅ Задача возвращена на форум!', show_alert=True)
                # Закрываем сцену редактирования, так как задача больше не у исполнителя
                await self.scene.end()
            else:
                error_msg = res.get('detail', 'Неизвестная ошибка') if isinstance(res, dict) else str(res)
                await callback.answer(f'❌ Ошибка: {error_msg}', show_alert=True)
        else:
            await callback.answer('❌ Ошибка: задача не найдена', show_alert=True)

