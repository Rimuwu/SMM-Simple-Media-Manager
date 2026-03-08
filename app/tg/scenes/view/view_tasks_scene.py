from tg.oms import Scene
from .filter_selection_page import FilterSelectionPage
from .task_list_page import TaskListPage
from .task_detail_page import TaskDetailPage
from .assign_executor_page import AssignExecutorPage
from .change_deadline_page import ChangeDeadlinePage
from .change_name_page import ChangeNamePage
from .change_description_page import ChangeDescriptionPage
from .select_user_filter_page import SelectUserFilterPage
from .select_department_filter_page import SelectDepartmentFilterPage
from modules.exec.brain_client import brain_client
from tg.oms.common_pages import DatePickerPage, ContactPage
from tg.scenes.edit.preview_page import PreviewPage
from .files_page import FilesPage_view
from .delete_confirm_page import DeleteConfirmPage

class ViewTasksScene(Scene):

    __scene_name__ = 'view-tasks'
    __pages__ = [
        FilterSelectionPage,
        TaskListPage,
        TaskDetailPage,
        AssignExecutorPage,
        ChangeDeadlinePage,
        ContactPage,
        ChangeNamePage,
        ChangeDescriptionPage,
        SelectUserFilterPage,
        SelectDepartmentFilterPage,
        DatePickerPage,
        PreviewPage,
        FilesPage_view,
        DeleteConfirmPage
    ]

    # Привязываем функции для работы с БД
    __insert_function__ = staticmethod(brain_client.insert_scene)
    __load_function__ = staticmethod(brain_client.load_scene)
    __update_function__ = staticmethod(brain_client.update_scene)
    __delete_function__ = staticmethod(brain_client.delete_scene)

    async def get_card_data(self):
        """Получает данные задачи по её ID"""
        task_id = self.data['scene'].get('selected_task')
        if not task_id:
            return None

        tasks = await brain_client.get_cards(card_id=task_id)
        if not tasks:
            return None

        return tasks[0]