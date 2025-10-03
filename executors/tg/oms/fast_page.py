from .models.page import Page
from .models.text_page import TextTypeScene

page_type: dict[str] = {
    'text': TextTypeScene
}

def fast_page(page_type_str: str, 
              page_name: str) -> type[Page]:
    """ Быстрый доступ к типам страниц по строковому идентификатору """
    base_cls = page_type.get(page_type_str, Page)

    class Modified(base_cls): 
        __page_name__ = page_name

    return Modified