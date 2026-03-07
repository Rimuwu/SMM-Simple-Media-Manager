from global_modules import brain_client
from tg.oms.models.text_page import TextTypeScene
from tg.oms.utils import callback_generator
from aiogram.types import Message
import re

class ContentSetterPage(TextTypeScene):
    
    __page_name__ = 'content-setter'
    __scene_key__ = 'content'
    checklist = False

    # Режим установки контента: 'all' (общий) или ключ конкретного клиента
    content_mode = 'all'
    __max_length__ = 1024
    
    async def _calculate_tags_length(self) -> int:
        """
        Вычисляет длину всех тегов с учетом суффиксов клиента.
        Возвращает общую длину тегов, которую нужно вычесть из max_length.
        """
        card = await self.scene.get_card_data()
        if not card:
            return 0
        
        tags = card.get('tags', [])
        if not tags:
            return 0
        
        # Определяем клиента для получения суффикса
        if self.content_mode == 'all':
            # Если общий режим, берем суффикс первого клиента
            clients = card.get('clients', [])
            if not clients:
                return 0
            client_key = clients[0]
        else:
            client_key = self.content_mode
        
        # Получаем суффикс клиента
        from modules.constants import CLIENTS, SETTINGS
        tag_suffix = CLIENTS.get(client_key, {}).get('tag_suffix', '')
        
        # Подсчитываем длину всех тегов
        total_length = 0
        for tag in tags:
            # Получаем отображаемое имя тега из настроек
            tag_info = SETTINGS.get('properties', {}).get('tags', {}).get('values', {}).get(tag, {})
            tag_name = tag_info.get('tag', tag)

            # Добавляем # если его нет
            if not tag_name.startswith("#"):
                tag_name = f"#{tag_name}"

            # Добавляем суффикс
            full_tag = f"{tag_name}{tag_suffix}"

            # +1 для переноса строки между тегами
            total_length += len(full_tag) + 1

        # +2 для двойного переноса строки перед блоком тегов
        if total_length > 0:
            total_length += 2

        return total_length

    def _convert_html_to_markdown(self, html_text: str) -> str:
        """Конвертирует HTML в Markdown формат согласно Telegram entities"""
        if not html_text:
            return ""
        
        text = html_text
        
        # Pre с языком: <pre language="c++">code</pre> → ```c++\ncode\n```
        # Обрабатываем ДО обычного <pre>, чтобы не потерять атрибут language
        text = re.sub(r'<pre language="([^"]*)">(.*?)</pre>', r'```\1\n\2\n```', text, flags=re.DOTALL)
        
        # Pre без языка: <pre>text</pre> → ```\ntext\n```
        text = re.sub(r'<pre>(.*?)</pre>', r'```\n\1\n```', text, flags=re.DOTALL)
        
        # Blockquote: <blockquote>text</blockquote> → каждая строка начинается с >
        def convert_blockquote(match):
            content = match.group(1)
            lines = content.split('\n')
            quoted_lines = [f'>{line}' for line in lines]
            return '\n'.join(quoted_lines)
        
        text = re.sub(r'<blockquote>(.*?)</blockquote>', convert_blockquote, text, flags=re.DOTALL)
        
        # Bold: <b>text</b> или <strong>text</strong> → **text**
        text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
        
        # Italic: <i>text</i> или <em>text</em> → *text*
        text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
        text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
        
        # Underline: <u>text</u> → __text__ (Markdown Extended)
        text = re.sub(r'<u>(.*?)</u>', r'__\1__', text, flags=re.DOTALL)
        
        # Strikethrough: <s>text</s> или <strike>text</strike> или <del>text</del> → ~~text~~
        text = re.sub(r'<s>(.*?)</s>', r'~~\1~~', text, flags=re.DOTALL)
        text = re.sub(r'<strike>(.*?)</strike>', r'~~\1~~', text, flags=re.DOTALL)
        text = re.sub(r'<del>(.*?)</del>', r'~~\1~~', text, flags=re.DOTALL)
        
        # Code: <code>text</code> → `text`
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', text, flags=re.DOTALL)
        
        # Links: <a href="url">text</a> → [text](url)
        text = re.sub(r'<a href="(.*?)">(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
        
        # Убираем оставшиеся HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Декодируем HTML entities
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#x27;', "'")
        text = text.replace('&nbsp;', ' ')
        
        return text

    async def content_worker(self) -> str:
        # Получаем карточку для доступа к content dict
        card = await self.scene.get_card_data()
        content_dict = card.get('content', {}) if card else {}

        tags_length = await self._calculate_tags_length()
        self.max_length = self.__max_length__ - tags_length

        # Если content_dict не dict (старый формат), инициализируем
        if not isinstance(content_dict, dict):
            content_dict = {'all': content_dict} if content_dict else {}
        
        # Получаем контент для текущего режима
        post = content_dict.get(self.content_mode, '')
        
        # Формируем заголовок в зависимости от режима
        if self.content_mode == 'all':
            mode_label = "Общий контент"
        else:
            from modules.constants import CLIENTS
            client_info = CLIENTS.get(self.content_mode, {})
            client_name = client_info.get('label', self.content_mode)
            mode_label = f"Контент для {client_name}"

        if not post:
            post = f'<i>Контент не задан для режима: {mode_label}</i>'
        else:
            # Конвертируем HTML в Markdown для отображения
            markdown_post = self._convert_html_to_markdown(post)
            post = f'<pre language="{mode_label}">{markdown_post}</pre>'

        return self.append_variables(content_block=post)

    async def buttons_worker(self) -> list[dict]:
        buttons_list = await super().buttons_worker()
        
        # Кнопка переключения режима контента
        if not self.checklist:
            # Получаем список доступных клиентов
            card = await self.scene.get_card_data()
            clients = card.get('clients', []) if card else []
            
            buttons_list.append({
                'text': '📑 Памятка',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'checklist'),
                'ignore_row': True
            })
            
            if clients:
                # Добавляем кнопку смены режима
                if self.content_mode == 'all':
                    buttons_list.append({
                        'text': '🔄 Режим: Общий контент',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__, 'switch_mode')
                    })
                else:
                    from modules.constants import CLIENTS
                    client_info = CLIENTS.get(self.content_mode, {})
                    client_name = client_info.get('label', self.content_mode)
                    buttons_list.append({
                        'text': f'🔄 Режим: {client_name}',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__, 'switch_mode'),
                        "ignore_row": True
                    })
            
            # Кнопка очистки контента
            buttons_list.append({
                'text': '🗑 Очистить контент',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'clear_content'),
                'ignore_row': True
            })

        else:
            buttons_list.append({
                'text': '📑 Контент',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_content')
            })

        return buttons_list

    @TextTypeScene.on_callback('switch_mode')
    async def switch_mode(self, callback, args):
        """Переключение между режимами установки контента"""
        card = await self.scene.get_card_data()
        clients = card.get('clients', []) if card else []
        
        if not clients:
            await callback.answer("❌ Сначала выберите каналы для публикации")
            return
        
        # Создаем список доступных режимов: 'all' + клиенты
        available_modes = ['all'] + clients
        
        # Находим текущий индекс
        try:
            current_index = available_modes.index(self.content_mode)
        except ValueError:
            current_index = 0
        
        # Переключаемся на следующий режим (циклично)
        next_index = (current_index + 1) % len(available_modes)
        self.content_mode = available_modes[next_index]

        # Обновляем сообщение
        self.clear_content()
        # await self.content_worker()
        await self.scene.update_message()


    @TextTypeScene.on_callback('clear_content')
    async def clear_content_handler(self, callback, args):
        """Обработчик очистки контента"""
        task_id = self.scene.data['scene'].get('task_id')
        if not task_id:
            await callback.answer("❌ Задача не найдена")
            return
        
        # Определяем client_key в зависимости от режима
        client_key = None if self.content_mode == 'all' else self.content_mode
        
        # Отправляем запрос на очистку контента
        ok = await brain_client.clear_content(task_id, client_key)
        
        if ok:
            # Обновляем отображение
            self.clear_content()
            # await self.content_worker()
            await self.scene.update_message()
            
            # Показываем уведомление
            if self.content_mode == 'all':
                await callback.answer("✅ Общий контент очищен")
            else:
                from modules.constants import CLIENTS
                client_info = CLIENTS.get(self.content_mode, {})
                client_name = client_info.get('label', self.content_mode)
                await callback.answer(f"✅ Контент для {client_name} очищен")
        else:
            await callback.answer("❌ Ошибка очистки контента")

    @TextTypeScene.on_callback('to_content')
    async def to_content(self, callback, args):
        self.clear_content()
        # await self.content_worker()

        self.checklist = False
        await self.scene.update_message()

    @TextTypeScene.on_callback('checklist')
    async def show_checklist(self, callback, args):
        checklist_text = (
            "📑 <b>Памятка по написанию поста:</b>\n\n"
            "1. Текст должен быть написан на «ты», конкретным и емким.\n"
            "2. Используйте корректное тире (`–`) и ставьте пробелы после смайликов.\n"
            "3. После каждого абзаца должна быть пустая строка.\n"
            "4. При перечислении используйте «;» и «.» в конце пунктов, корректно цитируйте («текст»).\n"
            "5. Ссылки должны быть укорочены или скрыты под гиперссылку.\n"
            "6. Избегайте длинных сложных предложений."
            "\n\n"
            "<a href=\"https://docs.google.com/document/d/18Jp7d1pseL84vlkA4D6ORcXCvJNOnCL66gtb7SNWUAE/edit?tab=t.0\">Ссылка на памятку</a>"
        )

        self.content = checklist_text

        self.checklist = True
        await self.scene.update_message()

    @TextTypeScene.on_text('str')
    async def handle_text(self, message: Message, value: str):
        # Получаем текст в HTML формате (сохраняем форматирование)
        text = message.text or ""
        html_text = message.html_text or text

        self.clear_content()
        if self.checklist: return
    
        # Вычисляем длину тегов и корректируем max_length
        tags_length = await self._calculate_tags_length()
        adjusted_max_length = self.__max_length__ - tags_length

        if len(text) > adjusted_max_length:
            self.content += f"\n\n❗️ Текст слишком длинный. Максимальная длина: {adjusted_max_length} символов (с учётом тегов: {tags_length} символов). Длина сейчас: {len(text)}."
            await self.scene.update_message()
            return 'error'

        if len(text) > self.max_length:
            self.content += f"\n\n❗️ Текст слишком длинный. Максимальная длина: {self.max_length} символов. Длинна сейчас: {len(text)}."
            await self.scene.update_message()
            return 'error'

        # Обновляем карточку через новый API эндпоинт /card/set-content
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            # Определяем client_key в зависимости от режима
            client_key = None if self.content_mode == 'all' else self.content_mode

            await brain_client.set_content(
                card_id=task_id,
                content=html_text,
                client_key=client_key
            )

        self.clear_content()
        await self.scene.update_message()
