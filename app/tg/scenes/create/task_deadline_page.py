from tg.oms import Page
from tg.oms.utils import callback_generator
from aiogram.types import Message
from datetime import datetime


class TaskDeadlinePage(Page):
    """Страница ввода дедлайна задания."""

    __page_name__ = 'task-deadline'

    async def data_preparate(self) -> None:
        task = self.scene.data.get('task', {})
        deadline = task.get('deadline')
        if deadline:
            try:
                dt = datetime.fromisoformat(deadline)
                deadline_str = dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                deadline_str = deadline
        else:
            deadline_str = 'Не установлен'
        self.content = (
            f"📅 *Дедлайн задания*\n\n"
            f"Текущий: *{deadline_str}*\n\n"
            f"Введите дату в формате:\n"
            f"`ЧЧ:ММ ДД.ММ.ГГГГ` / `ЧЧ:ММ` / `ЧЧ:ММ ДД.ММ` / `ДД.ММ.ГГГГ` / `ДД.ММ`"
        )

    async def buttons_worker(self) -> list[dict]:
        return [{
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__, 'task_deadline_back'),
        }]

    @Page.on_callback('task_deadline_back')
    async def back(self, callback, args):
        await self.scene.update_page('task-main')

    @Page.on_text('time')
    async def handle_time(self, message: Message, value):
        await self.scene.update_key('task', 'deadline', value.isoformat())
        await self.scene.update_page('task-main')

    @Page.on_text('not_handled')
    async def not_handled(self, message: Message):
        self.content += '\n\n❗️ Некорректный формат даты. Попробуйте ещё раз.'
        await self.scene.update_message()
