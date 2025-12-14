from tg.scenes.create.user_page import UserPage
from tg.oms import Scene
from .channels_page import ChannelsPage
from .date_page import DatePage
from .main_page import MainPage
from .finish_page import FinishPage
from .tags_page import TagsPage
from .files_page import FilesPage
from global_modules.brain_client import brain_client
from .cancel import CancelPage
from .image import Image
from .send_page import SendDatePage
from tg.oms.common_pages import DatePickerPage
from .ai_parse_page import AIParserPage
from .editor_check_page import EditorCheckPage

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
        # date picker
        DatePickerPage,
    ]

    # Привязываем функции для работы с БД
    __insert_function__ = staticmethod(brain_client.insert_scene)
    __load_function__ = staticmethod(brain_client.load_scene)
    __update_function__ = staticmethod(brain_client.update_scene)
    __delete_function__ = staticmethod(brain_client.delete_scene)
