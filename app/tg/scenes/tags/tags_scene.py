from tg.oms import Scene
from .pages.tags_list_page import TagsListPage
from .pages.tag_detail_page import TagDetailPage
from .pages.tag_edit_pages import TagEditTextPage, TagEditIntPage
from .pages.tag_create_pages import TagCreateKeyPage, TagCreateNamePage, TagCreateHashtagPage
from models.Scene import Scene as SceneModel


class TagsScene(Scene):
    __scene_name__ = 'tags'
    __pages__ = [
        TagsListPage,
        TagDetailPage,
        TagEditTextPage,
        TagEditIntPage,
        TagCreateKeyPage,
        TagCreateNamePage,
        TagCreateHashtagPage,
    ]

    __insert_function__ = staticmethod(SceneModel.insert_scene)
    __load_function__ = staticmethod(SceneModel.load_scene)
    __update_function__ = staticmethod(SceneModel.update_scene)
    __delete_function__ = staticmethod(SceneModel.delete_scene)
