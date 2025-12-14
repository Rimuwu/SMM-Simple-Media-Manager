"""
Общие переиспользуемые классы страниц для OMS
"""
from .date_input_page import DateInputPage
from .tags_selector_page import TagsSelectorPage
from .user_selector_page import UserSelectorPage
from .channels_selector_page import ChannelsSelectorPage
from .update_text_page import UpdateTextPage
from .date_picker_pages import DatePickerPage

__all__ = ['DateInputPage', 'TagsSelectorPage', 'UserSelectorPage', 'ChannelsSelectorPage', 'UpdateTextPage', 'DatePickerPage']
