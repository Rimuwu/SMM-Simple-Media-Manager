from enum import Enum

class KaitenBoardNames(str, Enum):
    QUEUE = "queue"
    IN_PROGRESS = "in_progress"

class PropertyNames(str, Enum):
    CHANNELS = "channels"
    TAGS = "tags"

class ApiEndpoints(str, Enum):
    FORUM_SEND_MESSAGE = "/forum/send-message-to-forum"
    FORUM_UPDATE_MESSAGE = "/forum/update-forum-message"
    FORUM_DELETE_MESSAGE = "/forum/delete-forum-message/{}"
    COMPLETE_SEND_PREVIEW = "/forum/send-complete-preview"
    COMPLETE_UPDATE_PREVIEW = "/forum/update-complete-preview"
    COMPLETE_DELETE_PREVIEW = "/forum/delete-complete-preview"
    NOTIFY_USER = "/events/notify_user"
    UPDATE_SCENES = "/events/update_scenes"

class SceneNames(str, Enum):
    USER_TASK = "user-task"

class Messages(str, Enum):
    TASK_TAKEN = "Задание взято в работу"
    DEADLINE_CHANGED = "Дедлайн изменен"
    NEW_TASK = "🆕 Новая задача"
    NEW_COMMENT = "💬 Новый комментарий к задаче"
    CHANGE_NOTIFICATION = "🔔 Изменение в задаче"
