from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Post, Reaction, User


@dataclass
class UserStats:
    reposts_made: int
    reposts_received: int
    points: float
    weight: float


async def get_user_stats(session: AsyncSession, user: User) -> UserStats:
    # Count reposts made (reactions given to others' posts)
    reposts_made_stmt = (
        select(func.count(Reaction.id))
        .join(Post, Reaction.post_id == Post.id)
        .where(Reaction.reactor_user_id == user.id, Post.user_id != user.id)
    )
    reposts_made_result = await session.execute(reposts_made_stmt)
    reposts_made = reposts_made_result.scalar() or 0

    # Count reposts received (reactions on user's posts from others)
    reposts_received_stmt = (
        select(func.count(Reaction.id))
        .join(Post, Reaction.post_id == Post.id)
        .where(Post.user_id == user.id, Reaction.reactor_user_id != user.id)
    )
    reposts_received_result = await session.execute(reposts_received_stmt)
    reposts_received = reposts_received_result.scalar() or 0

    return UserStats(
        reposts_made=reposts_made,
        reposts_received=reposts_received,
        points=user.points,
        weight=user.weight,
    )


async def get_leaderboard(
    session: AsyncSession, limit: int = 10
) -> list[tuple[User, UserStats]]:
    stmt = select(User).order_by(User.points.desc()).limit(limit)
    result = await session.execute(stmt)
    users = result.scalars().all()

    leaderboard = []
    for user in users:
        stats = await get_user_stats(session, user)
        leaderboard.append((user, stats))

    return leaderboard
