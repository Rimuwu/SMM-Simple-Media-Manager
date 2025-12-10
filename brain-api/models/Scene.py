from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON
from database.connection import Base
from database.crud_mixins import AsyncCRUDMixin
from database.annotated_types import createAT, updateAT


class Scene(Base, AsyncCRUDMixin):
    __tablename__ = "scenes"

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
