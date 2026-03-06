from tg.oms.common_pages import DateInputPage


class DatePage(DateInputPage):
    
    __page_name__ = 'publish-date'
    __scene_key__ = 'publish_date'
    __next_page__ = 'main'
    
    update_to_db = False