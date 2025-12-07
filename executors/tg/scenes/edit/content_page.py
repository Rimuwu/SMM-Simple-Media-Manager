from tg.oms.models.text_page import TextTypeScene
from global_modules.brain_client import brain_client
from tg.oms.utils import callback_generator
from aiogram.types import Message, MessageEntity
import re

class ContentSetterPage(TextTypeScene):
    
    __page_name__ = 'content-setter'
    __scene_key__ = 'content'
    __next_page__ = 'main-page'
    checklist = False
    
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
    
    async def data_preparate(self) -> None:
        await super().data_preparate()

    async def content_worker(self) -> str:
        post = self.scene.get_key('scene', 'content')

        if not post:
            post = '<i>Контент не задан.</i>'
        else:
            # Конвертируем HTML в Markdown для отображения
            markdown_post = self._convert_html_to_markdown(post)
            post = f'<pre language="Контент">{markdown_post}</pre>'

        return self.append_variables(content_block=post)

    async def buttons_worker(self) -> list[dict]:
        buttons_list = await super().buttons_worker()

        if not self.checklist:
            buttons_list.append({
                'text': '📑 Памятка',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'checklist')
            })
        else:
            buttons_list.append({
                'text': '📑 Контент',
                'callback_data': callback_generator(
                    self.scene.__scene_name__, 'to_content')
            })

        return buttons_list

    @TextTypeScene.on_callback('to_content')
    async def to_content(self, callback, args):
        self.clear_content()
        await self.content_worker()

        self.checklist = False
        await self.scene.update_message()

    @TextTypeScene.on_callback('checklist')
    async def show_checklist(self, callback, args):
        checklist_text = (
            "📑 **Памятка по написанию поста:**\n\n"
            "1. Текст должен быть написан на «ты», конкретным и емким.\n"
            "2. Используйте корректное тире (`–`) и ставьте пробелы после смайликов.\n"
            "3. После каждого абзаца должна быть пустая строка.\n"
            "4. При перечислении используйте «;» и «.» в конце пунктов, корректно цитируйте («текст»).\n"
            "5. Ссылки должны быть укорочены или скрыты под гиперссылку.\n"
            "6. Избегайте длинных сложных предложений."
            "\n\n"
            "[Ссылка на памятку](https://docs.google.com/document/d/18Jp7d1pseL84vlkA4D6ORcXCvJNOnCL66gtb7SNWUAE/edit?tab=t.0)"
        )

        self.content = checklist_text

        self.checklist = True
        await self.scene.update_message()

    @TextTypeScene.on_text('str')
    async def handle_text(self, message: Message, value: str):
        # Получаем текст в HTML формате (сохраняем форматирование)
        text = message.text or ""
        print(message.md_text)
        html_text = message.html_text or text

        self.clear_content()
        if self.checklist: return

        if len(text) < self.min_length:
            self.content += f"\n\n❗️ Текст слишком короткий. Минимальная длина: {self.min_length} символов. Длинна сейчас: {len(text)}."
            await self.scene.update_message()
            return

        if len(text) > self.max_length:
            self.content += f"\n\n❗️ Текст слишком длинный. Максимальная длина: {self.max_length} символов. Длинна сейчас: {len(text)}."
            await self.scene.update_message()
            return

        # Сохраняем контент в HTML формате (для хранения)
        await self.scene.update_key('scene', self.scene_key, html_text)
        
        # Обновляем карточку (сохраняем в HTML)
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            await brain_client.update_card(
                card_id=task_id,
                content=html_text
            )

        # Переходим к следующей странице
        if self.next_page:
            await self.scene.update_page(self.next_page)
        else:
            self.clear_content()
            await self.scene.update_message()
