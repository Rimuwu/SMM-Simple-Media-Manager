from tg.oms import Scene
from .filter_selection_page import FilterSelectionPage
from .task_list_page import TaskListPage
from .task_detail_page import TaskDetailPage

class ViewTasksScene(Scene):

    __scene_name__ = 'view-tasks'
    __pages__ = [
        FilterSelectionPage,
        TaskListPage,
        TaskDetailPage
    ]