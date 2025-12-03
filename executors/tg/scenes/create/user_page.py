from tg.oms.common_pages import UserSelectorPage


class UserPage(UserSelectorPage):

    __page_name__ = 'user'
    __scene_key__ = 'user'
    __next_page__ = 'main'
    
    update_to_db = False
    allow_reset = True
    filter_department = 'smm'  # Фильтруем только пользователей из SMM департамента