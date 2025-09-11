from datetime import datetime
from typing import Optional
from sqlalchemy import select

from models.Card import Card, CardStatus
from database.connection import session_factory
from uuid import UUID


class CardService:
    """Сервис для работы с карточками"""

    @staticmethod
    async def create_card(
        name: str,
        description: Optional[str],
        customer_id: Optional[UUID],
        executor_id: Optional[UUID],
        clients: list[str],
        tags: list[str],
        need_check: bool = True,
        time_send: Optional[datetime] = None,
        deadline: Optional[datetime] = None,
        status: CardStatus = CardStatus.pass_,
    ) -> Card:
        """Создать карточку"""
        async with session_factory() as session:
            new_card = Card(
                status=status,
                name=name,
                description=description,
                customer_id=customer_id,
                executor_id=executor_id,
                clients=clients,
                need_check=need_check,
                tags=tags,
                time_send=time_send,
                deadline=deadline
            )
            session.add(new_card)
            await session.commit()
            await session.refresh(new_card)
            return new_card

    @staticmethod
    async def delete_card(card_id: UUID) -> bool:
        """Удалить карточку"""
        async with session_factory() as session:
            stmt = select(Card).where(
                Card.id == card_id
            )
            result = await session.execute(stmt)
            card = result.scalar_one_or_none()

            if card:
                await session.delete(card)
                await session.commit()
                return True

        return False

    @staticmethod
    async def get_all_cards() -> list[Card]:
        """Получить все карточки"""
        async with session_factory() as session:
            stmt = select(Card)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def get_by_id(card_id: UUID) -> Optional[Card]:
        """Получить карточку по ID"""
        async with session_factory() as session:
            stmt = select(Card).where(
                Card.card_id == card_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_status(status: CardStatus) -> list[Card]:
        """Получить карточки по статусу"""
        async with session_factory() as session:
            stmt = select(Card).where(
                Card.status == status
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())