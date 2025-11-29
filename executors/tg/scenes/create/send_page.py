from tg.oms.common_pages import DateInputPage


class SendDatePage(DateInputPage):
    
    __page_name__ = 'send-date'
    __scene_key__ = 'send_date'
    __next_page__ = 'main'
    
    update_to_db = False