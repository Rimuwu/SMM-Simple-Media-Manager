from tg.oms import Scene
from .main_page import MainPage

class TaskScene(Scene):
    
    __scene_name__ = 'user-task'
    __pages__ = [
        MainPage
        
    ]