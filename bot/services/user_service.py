from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None = None
) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()
    elif username and user.username != username:
        user.username = username
        await session.flush()

    return user


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    clean_username = username.lstrip("@")
    stmt = select(User).where(User.username == clean_username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def set_user_weight(session: AsyncSession, user: User, weight: float) -> None:
    user.weight = weight
    await session.flush()


async def update_user_points(
    session: AsyncSession, user: User, points_delta: float
) -> None:
    user.points += points_delta
    await session.flush()
