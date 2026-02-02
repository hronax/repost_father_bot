from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Post, Reaction, User


async def create_post(
    session: AsyncSession,
    user: User,
    message_id: int,
    chat_id: int,
    topic_id: int | None = None,
) -> Post:
    post = Post(
        user_id=user.id,
        message_id=message_id,
        chat_id=chat_id,
        topic_id=topic_id,
    )
    session.add(post)
    await session.flush()
    return post


async def get_post_by_message(
    session: AsyncSession, message_id: int, chat_id: int
) -> Post | None:
    stmt = (
        select(Post)
        .options(selectinload(Post.user))
        .where(Post.message_id == message_id, Post.chat_id == chat_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_reaction(
    session: AsyncSession, post: Post, reactor: User
) -> Reaction | None:
    # Check if reaction already exists
    stmt = select(Reaction).where(
        Reaction.post_id == post.id, Reaction.reactor_user_id == reactor.id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        return None

    reaction = Reaction(post_id=post.id, reactor_user_id=reactor.id)
    session.add(reaction)
    await session.flush()
    return reaction


async def reaction_exists(
    session: AsyncSession, post_id: int, reactor_user_id: int
) -> bool:
    stmt = select(Reaction).where(
        Reaction.post_id == post_id, Reaction.reactor_user_id == reactor_user_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
