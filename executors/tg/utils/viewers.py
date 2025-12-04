from datetime import datetime, timedelta

class ViewersManager:
    def __init__(self):
        self._viewers = {}  # {task_id: {user_id: {name: str, last_seen: datetime}}}

    def update_viewer(self, task_id: str, user_id: int, user_name: str):
        if task_id not in self._viewers:
            self._viewers[task_id] = {}
        
        self._viewers[task_id][user_id] = {
            'name': user_name,
            'last_seen': datetime.now()
        }
        
        # Cleanup old viewers for this task
        self._cleanup(task_id)

    def get_viewers(self, task_id: str, exclude_user_id: int = None) -> list[str]:
        self._cleanup(task_id)
        if task_id not in self._viewers:
            return []
            
        viewers = []
        for uid, data in self._viewers[task_id].items():
            if exclude_user_id and uid == exclude_user_id:
                continue
            viewers.append(data['name'])
            
        return viewers

    def _cleanup(self, task_id: str):
        if task_id not in self._viewers:
            return
            
        now = datetime.now()
        to_remove = []
        for uid, data in self._viewers[task_id].items():
            if now - data['last_seen'] > timedelta(minutes=5):
                to_remove.append(uid)
                
        for uid in to_remove:
            del self._viewers[task_id][uid]
            
        if not self._viewers[task_id]:
            del self._viewers[task_id]

viewers_manager = ViewersManager()
