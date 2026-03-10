from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import createAT, updateAT, uuidPK


class Scene(Base, AsyncCRUDMixin):
    __tablename__ = "scenes"

    id: Mapped[uuidPK]
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False,
                                         index=True, primary_key=True
                                         )

    scene: Mapped[str] = mapped_column(String, nullable=False)
    scene_path: Mapped[str] = mapped_column(String, nullable=False)
    page: Mapped[str] = mapped_column(String, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    created_at: Mapped[createAT]
    updated_at: Mapped[updateAT]

    def __repr__(self) -> str:
        return f"<Scene(user_id={self.user_id}, scene='{self.scene}', page='{self.page}')>"

    # ── Методы для совместимости с OMS (возвращают словари) ──────────────────

    @classmethod
    async def insert_scene(cls, user_id: int, data: dict) -> bool:
        """Создать запись сцены для пользователя. Пропускает, если уже существует."""
        existing = await cls.get_by_key("user_id", user_id)
        if existing:
            return False
        await cls.create(
            user_id=user_id,
            scene=data.get("scene", ""),
            scene_path=data.get("scene_path", ""),
            page=data.get("page", ""),
            message_id=data.get("message_id", 0),
            data=data.get("data", {}),
        )
        return True

    @classmethod
    async def load_scene(cls, user_id: int) -> "dict | None":
        """Загрузить данные сцены для пользователя."""
        scene = await cls.get_by_key("user_id", user_id)
        return scene.to_dict() if scene else None

    @classmethod
    async def update_scene(cls, user_id: int, data: dict) -> bool:
        """Обновить данные сцены для пользователя."""
        scene = await cls.get_by_key("user_id", user_id)
        if not scene:
            return False
        updates = {
            k: data[k]
            for k in ("scene", "scene_path", "page", "message_id", "data")
            if k in data and data[k] is not None
        }
        if "data" in updates:
            updates["data"] = cls._serialize_for_json(updates["data"])
        if updates:
            await scene.update(**updates)
        return True

    @classmethod
    async def delete_scene(cls, user_id: int) -> bool:
        """Удалить сцену пользователя."""
        scene = await cls.get_by_key("user_id", user_id)
        if scene:
            await scene.delete()
        return True

    @classmethod
    async def all_scenes(cls) -> list[dict]:
        """Все сцены в виде списка словарей."""
        scenes = await cls.get_all()
        return [s.to_dict() for s in scenes]

    @staticmethod
    def _serialize_for_json(obj):
        """Рекурсивно приводит UUID, datetime и enum к JSON-совместимым типам."""
        from datetime import datetime as _dt
        from uuid import UUID as _UUID

        if isinstance(obj, _UUID):
            return str(obj)
        if isinstance(obj, _dt):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: Scene._serialize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [Scene._serialize_for_json(item) for item in obj]
        if hasattr(obj, "__dict__") and hasattr(obj, "__class__"):
            return str(obj)
        return obj


    async def update_task_scene(self
    ): pass

    async def close_user_scene(self
    ): pass

    async def close_card_related_scenes(self
    ): pass

    async def update_scenes(self
    ): pass