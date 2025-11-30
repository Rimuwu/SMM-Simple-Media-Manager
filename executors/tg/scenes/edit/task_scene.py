from tg.oms import Scene

from modules.api_client import get_cards, update_card, insert_scene, load_scene, update_scene, delete_scene
from .channels_page import ChannelsSettingsPage
from .content_page import ContentSetterPage
from .publish_date_page import PublishDateSetterPage
from .status_page import StatusSetterPage
from .ai_check_page import AICheckPage
from .tags_page import TagsSetterPage
from .main_page import MainPage
from .files_page import FilesPage
from .preview_page import PreviewPage
from .editor_notes_page import EditorNotesPage

class TaskScene(Scene):

    __scene_name__ = 'user-task'
    __pages__ = [
        MainPage,
        ChannelsSettingsPage,
        ContentSetterPage,
        PublishDateSetterPage,
        StatusSetterPage,
        AICheckPage,
        TagsSetterPage,
        FilesPage,
        PreviewPage,
        EditorNotesPage
    ]

    # Привязываем функции для работы с БД
    __insert_function__ = staticmethod(insert_scene)
    __load_function__ = staticmethod(load_scene)
    __update_function__ = staticmethod(update_scene)
    __delete_function__ = staticmethod(delete_scene)
    
    def set_taskid(self, task_id: int):
        """Устанавливает ID задачи в данные сцены"""
        self.data['scene']['task_id'] = task_id

    async def start(self):
        card = await self.get_card_data()
        if not card:
            await self.__bot__.send_message(
                self.user_id,
                "Задача не найдена."
            )
            return

        await self.insert_to_db()
        await self.save_to_db()
        await self.send_message()

    async def get_card_data(self):
        """Получает данные задачи по её ID"""
        task_id = self.data['scene'].get('task_id')
        if not task_id:
            return None

        tasks = await get_cards(card_id=task_id)
        if not tasks:
            return None

        return tasks[0]