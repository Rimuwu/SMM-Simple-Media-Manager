from tg.scenes.create.user_page import UserPage
from tg.oms import Scene
from .channels_page import ChannelsPage
from .date_page import DatePage
from .main_page import MainPage
from .finish_page import FinishPage
from .tags_page import TagsPage
from .files_page import FilesPage
from modules.api_client import insert_scene, load_scene, update_scene, delete_scene
from .cancel import CancelPage
from .image import Image
from .send_page import SendDatePage
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
        EditorCheckPage
    ]

    # Привязываем функции для работы с БД
    __insert_function__ = staticmethod(insert_scene)
    __load_function__ = staticmethod(load_scene)
    __update_function__ = staticmethod(update_scene)
    __delete_function__ = staticmethod(delete_scene)