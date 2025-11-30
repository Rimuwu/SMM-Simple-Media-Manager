from tg.oms import Scene
from .pages.users_list_page import UsersListPage
from .pages.user_detail_page import UserDetailPage
from .pages.add_user_page import AddUserPage
from .pages.select_role_page import SelectRolePage
from .pages.select_kaiten_user_page import SelectKaitenUserPage
from modules.api_client import insert_scene, load_scene, update_scene, delete_scene

class UsersScene(Scene):
    __scene_name__ = 'users'
    __pages__ = [
        UsersListPage,
        UserDetailPage,
        AddUserPage,
        SelectRolePage,
        SelectKaitenUserPage
    ]


    __insert_function__ = staticmethod(insert_scene)
    __load_function__ = staticmethod(load_scene)
    __update_function__ = staticmethod(update_scene)
    __delete_function__ = staticmethod(delete_scene)