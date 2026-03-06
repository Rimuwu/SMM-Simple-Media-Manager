from tg.oms import Scene
from .pages.users_list_page import UsersListPage
from .pages.user_detail_page import UserDetailPage
from .pages.add_user_page import AddUserPage
from .pages.select_role_page import SelectRolePage
from .pages.select_kaiten_user_page import SelectKaitenUserPage
from .pages.select_department_page import SelectDepartmentPage
from .pages.edit_about_page import EditAboutPage
from .pages.filter_users_by_role_page import FilterUsersByRolePage
from .pages.filter_users_by_department_page import FilterUsersByDepartmentPage
from global_modules.brain_client import brain_client

class UsersScene(Scene):
    __scene_name__ = 'users'
    __pages__ = [
        UsersListPage,
        UserDetailPage,
        AddUserPage,
        SelectRolePage,
        SelectKaitenUserPage,
        SelectDepartmentPage,
        EditAboutPage,
        FilterUsersByRolePage,
        FilterUsersByDepartmentPage
    ]


    __insert_function__ = staticmethod(brain_client.insert_scene)
    __load_function__ = staticmethod(brain_client.load_scene)
    __update_function__ = staticmethod(brain_client.update_scene)
    __delete_function__ = staticmethod(brain_client.delete_scene)
