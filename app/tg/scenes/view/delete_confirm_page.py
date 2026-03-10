from tg.oms import Page
from tg.oms.utils import callback_generator
from modules.card import card_service
from app.modules.components.logs import logger


class DeleteConfirmPage(Page):
    __page_name__ = 'delete-confirm'

    async def content_worker(self) -> str:
        task = self.scene.data['scene'].get('current_task_data', {})
        task_name = task.get('name', 'Без названия') if task else 'Без названия'
        return self.append_variables(task_name=task_name)

    async def buttons_worker(self) -> list[dict]:
        return [
            {
                'text': '✅ Да, удалить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'confirm_delete',
                    'yes'
                ),
                'ignore_row': True
            },
            {
                'text': '❌ Нет, отменить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'confirm_delete',
                    'no'
                ),
                'ignore_row': True
            }
        ]

    @Page.on_callback('confirm_delete')
    async def on_confirm(self, callback, args):
        action = args[1]

        if action == 'no':
            await self.scene.update_page('task-detail')
            return

        task = self.scene.data['scene'].get('current_task_data')
        if not task:
            await self.scene.update_page('task-detail')
            return

        card_id = task.get('card_id')
        if not card_id:
            await self.scene.update_page('task-detail')
            return

        logger.info(f"Пользователь {self.scene.user_id} подтвердил удаление задачи {card_id}")

        result = await card_service.destroy_card(card_id)
        success = result if isinstance(result, bool) else result.get('status', 500) == 200

        if success:
            logger.info(f"Задача {card_id} успешно удалена пользователем {self.scene.user_id}")
            await self.scene.update_key('scene', 'selected_task', None)
            await self.scene.update_key('scene', 'current_task_data', None)
            await self.scene.update_page('task-list')
            await callback.answer("🗑️ Задача успешно удалена.", show_alert=True)
        else:
            logger.error(f"Ошибка при удалении задачи {card_id}")
            await callback.answer("Ошибка при удалении", show_alert=True)
            await self.scene.update_page('task-detail')
