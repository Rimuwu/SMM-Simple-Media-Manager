from tg.oms import Page
from tg.oms.utils import callback_generator
from aiogram.types import Message


class TaskNamePage(Page):
    """Страница ввода названия задания."""

    __page_name__ = 'task-name'
    _validation_error: str = ''

    async def data_preparate(self) -> None:
        task = self.scene.data.get('task', {})
        name = task.get('name') or 'Не задано'
        self.content = (
            f"📌 *Название задания*\n\n"
            f"Текущее: `{name}`\n\n"
            f"Введите название задания (до 100 символов):"
        )
        if self._validation_error:
            self.content += f'\n\n{self._validation_error}'
            self._validation_error = ''

    async def buttons_worker(self) -> list[dict]:
        return [{
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__, 'task_name_back'),
        }]

    @Page.on_callback('task_name_back')
    async def back(self, callback, args):
        await self.scene.update_page('task-main')

    @Page.on_text('str')
    async def handle_text(self, message: Message, value: str):
        text = value.strip()
        if len(text) < 1:
            self._validation_error = '❗️ Название не может быть пустым.'
            await self.scene.update_message()
            return 'error'
        if len(text) > 100:
            self._validation_error = '❗️ Название слишком длинное (максимум 100 символов).'
            await self.scene.update_message()
            return 'error'
        await self.scene.update_key('task', 'name', text)
        await self.scene.update_page('task-main')
