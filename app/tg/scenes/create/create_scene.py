from tg.scenes.create.user_page import UserPage
from tg.oms import Scene
from .channels_page import ChannelsPage
from .date_page import DatePage
from .main_page import MainPage
from .finish_page import FinishPage
from .tags_page import TagsPage
from .files_page import FilesPage
from models.Scene import Scene as SceneModel
from .cancel import CancelPage
from .image import Image
from .send_page import SendDatePage
from tg.oms.common_pages import DatePickerPage
from .ai_parse_page import AIParserPage
from .editor_check_page import EditorCheckPage
from .help import HelpPage
from .task_main_page import TaskMainPage
from .task_name_page import TaskNamePage
from .task_description_page import TaskDescriptionPage
from .task_deadline_page import TaskDeadlinePage


class CreateTaskScene(Scene):

    __scene_name__ = 'create-task'
    __pages__ = [
        MainPage,
        ChannelsPage,
        DatePage,
        FinishPage,
        TagsPage,
        UserPage,
        FilesPage,
        CancelPage,
        Image,
        SendDatePage,
        AIParserPage,
        EditorCheckPage,
        DatePickerPage,
        HelpPage,
        # Task-level pages
        TaskMainPage,
        TaskNamePage,
        TaskDescriptionPage,
        TaskDeadlinePage,
        TaskExecutorPage,
    ]

    # Привязываем функции для работы с БД
    __insert_function__ = staticmethod(SceneModel.insert_scene)
    __load_function__ = staticmethod(SceneModel.load_scene)
    __update_function__ = staticmethod(SceneModel.update_scene)
    __delete_function__ = staticmethod(SceneModel.delete_scene)

    def __init__(self, user_id, bot_instance):
        super().__init__(user_id, bot_instance)
        # Инициализируем разделы для данных задания и списка постов
        if 'task' not in self.data:
            self.data['task'] = {'name': None, 'description': None, 'deadline': None}
        if 'cards' not in self.data:
            self.data['cards'] = []
