from tg.oms.models.text_page import TextTypeScene
from global_modules.brain_client import brain_client
from tg.oms.utils import callback_generator
from aiogram.types import Message, MessageEntity

class ContentSetterPage(TextTypeScene):
    
    __page_name__ = 'content-setter'
    __scene_key__ = 'content'
    __next_page__ = 'main-page'
    checklist = False
    
    def _convert_entities_to_markdown(self, text: str, entities: list[MessageEntity]) -> str:
        """Конвертирует Telegram entities в Markdown формат"""
        if not entities:
            return text
        
        # Сортируем entities по offset в обратном порядке
        sorted_entities = sorted(entities, key=lambda e: e.offset, reverse=True)
        
        result = text
        for entity in sorted_entities:
            start = entity.offset
            end = entity.offset + entity.length
            entity_text = text[start:end]
            
            # Конвертируем в зависимости от типа
            if entity.type == "bold":
                replacement = f"**{entity_text}**"
            elif entity.type == "italic":
                replacement = f"*{entity_text}*"
            elif entity.type == "code":
                replacement = f"`{entity_text}`"
            elif entity.type == "pre":
                language = entity.language or ""
                replacement = f"```{language}\n{entity_text}\n```"
            elif entity.type == "text_link":
                replacement = f"[{entity_text}]({entity.url})"
            elif entity.type == "underline":
                replacement = f"__{entity_text}__"
            elif entity.type == "strikethrough":
                replacement = f"~~{entity_text}~~"
            else:
                continue
            
            result = result[:start] + replacement + result[end:]
        
        return result
    
    async def data_preparate(self) -> None:
        await super().data_preparate()

    async def content_worker(self) -> str:
        post = self.scene.get_key('scene', 'content')

        if not post:
            post = '_Контент не задан._'
        else:
            post = f'```Контент {post}```'

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
        # Получаем текст и entities для форматирования
        text = message.text or ""
        entities = message.entities or []
        
        # Конвертируем entities в Markdown
        # formatted_text = self._convert_entities_to_markdown(text, entities)
        formatted_text = message.html_text or text

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

        # Сохраняем контент с форматированием в сцену
        await self.scene.update_key('scene', self.scene_key, formatted_text)
        
        # Обновляем карточку
        task_id = self.scene.data['scene'].get('task_id')
        if task_id:
            await brain_client.update_card(
                card_id=task_id,
                content=formatted_text
            )

        # Переходим к следующей странице
        if self.next_page:
            await self.scene.update_page(self.next_page)
        else:
            self.clear_content()
            await self.scene.update_message()
