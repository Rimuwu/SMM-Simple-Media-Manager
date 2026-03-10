from tg.oms import Page
from tg.oms.utils import callback_generator
from aiogram.types import Message


class TaskDescriptionPage(Page):
    """Страница ввода описания задания."""

    __page_name__ = 'task-description'
    _validation_error: str = ''

    async def data_preparate(self) -> None:
        task = self.scene.data.get('task', {})
        description = task.get('description') or 'Не задано'
        self.content = (
            f"📄 *Описание задания*\n\n"
            f"Текущее: `{description}`\n\n"
            f"Введите описание задания (до 2000 символов) или напишите «-» чтобы очистить:"
        )
        if self._validation_error:
            self.content += f'\n\n{self._validation_error}'
            self._validation_error = ''

    async def buttons_worker(self) -> list[dict]:
        return [{
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__, 'task_desc_back'),
        }]

    @Page.on_callback('task_desc_back')
    async def back(self, callback, args):
        await self.scene.update_page('task-main')

    @Page.on_text('str')
    async def handle_text(self, message: Message, value: str):
        text = value.strip()
        if text == '-':
            await self.scene.update_key('task', 'description', None)
            await self.scene.update_page('task-main')
            return
        if len(text) > 2000:
            self._validation_error = '❗️ Описание слишком длинное (максимум 2000 символов).'
            await self.scene.update_message()
            return 'error'
        await self.scene.update_key('task', 'description', text)
        await self.scene.update_page('task-main')
