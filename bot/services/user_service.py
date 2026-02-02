from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ChatUser, User


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


async def get_or_create_chat_user(
    session: AsyncSession, chat_id: int, telegram_id: int, username: str | None = None
) -> tuple[User, ChatUser]:
    """
    Ensure a global User row exists, then ensure a chat-scoped stats row exists.
    """
    user = await get_or_create_user(session, telegram_id, username)

    stmt = select(ChatUser).where(ChatUser.chat_id == chat_id, ChatUser.user_id == user.id)
    result = await session.execute(stmt)
    chat_user = result.scalar_one_or_none()
    if chat_user is None:
        chat_user = ChatUser(chat_id=chat_id, user_id=user.id)
        session.add(chat_user)
        await session.flush()

    return user, chat_user


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


async def set_chat_user_weight(session: AsyncSession, chat_user: ChatUser, weight: float) -> None:
    chat_user.weight = weight
    await session.flush()


async def update_user_points(
    session: AsyncSession, user: User, points_delta: float
) -> None:
    user.points += points_delta
    await session.flush()


async def update_chat_user_points(
    session: AsyncSession, chat_user: ChatUser, points_delta: float
) -> None:
    chat_user.points += points_delta
    await session.flush()
