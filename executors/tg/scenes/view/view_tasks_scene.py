from tg.oms import Scene
from .filter_selection_page import FilterSelectionPage
from .task_list_page import TaskListPage
from .task_detail_page import TaskDetailPage
from .assign_executor_page import AssignExecutorPage
from .change_deadline_page import ChangeDeadlinePage
from modules.api_client import insert_scene, load_scene, update_scene, delete_scene


class ViewTasksScene(Scene):

    __scene_name__ = 'view-tasks'
    __pages__ = [
        FilterSelectionPage,
        TaskListPage,
        TaskDetailPage,
        AssignExecutorPage,
        ChangeDeadlinePage
    ]

    # Привязываем функции для работы с БД
    __insert_function__ = staticmethod(insert_scene)
    __load_function__ = staticmethod(load_scene)
    __update_function__ = staticmethod(update_scene)
    __delete_function__ = staticmethod(delete_scene)