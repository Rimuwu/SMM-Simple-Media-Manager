from tg.scenes.create.user_page import UserPage
from tg.oms import Scene
from .channels_page import ChannelsPage
from .date_page import DatePage
from .main_page import MainPage
from .finish_page import FinishPage
from .tags_page import TagsPage

class CreateTaskScene(Scene):

    __scene_name__ = 'create-task'
    __pages__ = [
        MainPage,
        ChannelsPage,
        DatePage,
        FinishPage,
        TagsPage,
        UserPage
    ]