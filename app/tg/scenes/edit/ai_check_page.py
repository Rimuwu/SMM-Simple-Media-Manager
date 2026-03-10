import asyncio
from tg.oms import Page
from app.modules.components.logs import logger
from tg.oms.utils import callback_generator

class AICheckPage(Page):

    __page_name__ = 'ai-check'

    # Функция, вызываемая при получении результата от AI через events/ai_callback
    async def on_ai_result(self, result: str):
        """Обработка результата от AI: сохраняем ответ, снимаем индикатор загрузки и обновляем страницу."""
        try:
            await self.scene.update_key(self.__page_name__, 'ai_response', result)
            await self.scene.update_key(self.__page_name__, 'is_loading', False)
            if self.scene.current_page.__page_name__ == self.__page_name__:
                await self.scene.update_page(self.__page_name__)
        except Exception as e:
            logger.error(f"Error handling AI callback for user {self.scene.user_id}: {e}")

    async def data_preparate(self):
        """Подготовка данных страницы"""
        content = self.scene.data['scene'].get('content', '')

        if not content or content == 'Не указан':
            await self.scene.update_key(self.__page_name__, 'ai_response', None)
            await self.scene.update_key(self.__page_name__, 'is_loading', False)
            return

        # Проверяем, есть ли уже ответ
        page_data = self.scene.data.get(self.__page_name__, {})
        ai_response = page_data.get('ai_response')
        is_loading = page_data.get('is_loading', False)
        checked_content = page_data.get('checked_content')

        # Если контент изменился - сбрасываем кэш
        if checked_content != content:
            ai_response = None
            is_loading = False
            await self.scene.update_key(
                self.__page_name__, 'ai_response', None)
            await self.scene.update_key(
                self.__page_name__, 'is_loading', False)

        # Если нет ответа и не загружается - отправляем запрос к AI (fire-and-forget)
        if ai_response is None and not is_loading:
            await self.scene.update_key(
                self.__page_name__, 'is_loading', True)
            await self.scene.update_key(
                self.__page_name__, 'checked_content', content)

            # Отправляем запрос к AI в фоне — результат придёт в /events/ai_callback
            asyncio.create_task(self._send_ai_request(content))

    async def _send_ai_request(self, content: str):
        """Отправляет запрос к AI-сервису асинхронно (fire-and-forget).

        Включает в payload callback-метаданные (user_id, scene, page и имя функции),
        чтобы AI-сервис мог POST-ить результат в `/events/ai_callback`.
        """
        prompt = (
            "Проверь следующий текст на ошибки (орфографические, пунктуационные, стилистические).\n"
            "Текст должен быть написан на «ты», конкретным и емким. В некоторых случаях это не обязательно, так что это лишь рекомендация.\n"
            "Проверь корректность использования тире (–), смайликов (не более одного перед абзацем), пробелов после смайликов. Смайлики обычно ставятся перед абзацем.\n"
            "Убедись, что после каждого абзаца есть пустая строка.\n"
            "При перечислении проверь наличие «;» и «.» в конце пунктов, корректность цитирования («текст»).\n"
            "Ссылки должны быть укорочены или скрыты под гиперссылку.\n"
            "Избегай длинных сложных предложений.\n"
            "Текст предназанчен для публикации в каналах и пабликах вузовской организации.\n"
            "Запрещено использовать всё что связано с хеллоуином, лгбт, политикой, всем запрещённым в РФ.\n\n"
            "ЭТО КРИТИЧНО И ВСЕ ОШИБКИ ДОЛЖНЫ БЫТЬ ОТМЕЧЕНЫ, ОСОБЕННО - орфографические, пунктуационные, стилистические\n"
            "Не обращай внимание на html теги и спецсимволы, они там для форматирования.\n"
            f"Текст:\n{content}\n\n"
            "Ответь в формате:\n"
            "- Если есть ошибки или рекомендации: перечисли их с рекомендациями по исправлению\n"
        )

        payload = {
            'prompt': prompt,
            'callback': {
                'user_id': self.scene.user_id,
                'scene': self.scene.__scene_name__,
                'page': self.__page_name__,
                'function': 'on_ai_result'
            }
        }

        try:
            # Отправляем запрос и логируем, но не блокируем основной flow (это фоновой таск)
            from app.modules.components import ai as ai_module
            ai_module.send(payload)
        except Exception as e:
            logger.error(f"Exception while sending AI request for user {self.scene.user_id}: {e}")
            try:
                await self.scene.update_key(self.__page_name__, 'ai_response', '❌ **Ошибка при отправке запроса в AI. Попробуйте позже.**')
                await self.scene.update_key(self.__page_name__, 'is_loading', False)
                await self.scene.update_page(self.__page_name__)
            except Exception as e:
                logger.error(f"Error updating scene after exception: {e}")

    async def content_worker(self) -> str:
        self.clear_content()
        self.content = await super().content_worker()

        content = self.scene.data['scene'].get('content', '')

        if not content or content == 'Не указан':
            self.content += '\n\n❌ **Контент не указан**\n\nСначала добавьте контент поста, чтобы проверить его.'
            return self.content

        page_data = self.scene.data.get(self.__page_name__, {})
        ai_response = page_data.get('ai_response')
        is_loading = page_data.get('is_loading', False)

        if is_loading:
            self.content += '\n\n⏳ *Генерируется ответ...*\n\nПодождите, AI анализирует текст.'
        elif ai_response:
            self.content += f'\n\n🤖 *Результат проверки:*\n\n{ai_response}'
        else:
            self.content += '\n\n🔄 *Запуск проверки...*'

        return self.content

    async def buttons_worker(self):
        buttons = await super().buttons_worker()

        content = self.scene.data['scene'].get('content', '')
        page_data = self.scene.data.get(self.__page_name__, {})
        is_loading = page_data.get('is_loading', False)
        ai_response = page_data.get('ai_response')

        # Кнопка "Перепроверить" - только если есть контент и не загружается
        if content and content != 'Не указан' and not is_loading and ai_response:
            buttons.append({
                'text': '🔄 Перепроверить',
                'callback_data': 
                    callback_generator(
                        self.scene.__scene_name__,
                        'recheck'
                    )
            })

        return buttons



    @Page.on_callback('recheck')
    async def recheck_content(self, callback, args):
        """Перезапустить проверку — сбросим текущие данные и обновим страницу (новая проверка начнётся автоматически)."""
        # Сбрасываем кэш
        await self.scene.update_key(
            self.__page_name__, 'ai_response', None)
        await self.scene.update_key(
            self.__page_name__, 'is_loading', False)
        await self.scene.update_key(
            self.__page_name__, 'checked_content', None)

        # Обновляем страницу (это запустит новую проверку)
        await self.scene.update_page(self.__page_name__)
        await callback.answer('🔄 Запущена повторная проверка')
