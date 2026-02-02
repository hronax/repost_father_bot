from __future__ import annotations

from dataclasses import dataclass

from telegram import Bot, Chat as TgChat, ChatMember
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_config
from db.models import Chat, ChatAdmin


@dataclass(frozen=True)
class EffectiveChatSettings:
    hashtag: str
    reaction_emoji: str
    topic_id: int | None


async def get_chat(session: AsyncSession, chat_id: int) -> Chat | None:
    stmt = select(Chat).where(Chat.telegram_chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def require_chat(session: AsyncSession, chat_id: int) -> Chat:
    chat = await get_chat(session, chat_id)
    if chat is None:
        raise ValueError("Chat is not set up. Run /setup in the group first.")
    return chat


async def create_or_update_chat(
    session: AsyncSession,
    chat_id: int,
    title: str | None,
    *,
    topic_id: int | None = None,
) -> Chat:
    chat = await get_chat(session, chat_id)
    if chat is None:
        chat = Chat(telegram_chat_id=chat_id, title=title, topic_id=topic_id)
        session.add(chat)
        await session.flush()
        return chat

    # Update title/topic opportunistically
    if title and chat.title != title:
        chat.title = title
    if topic_id is not None and chat.topic_id != topic_id:
        chat.topic_id = topic_id
    await session.flush()
    return chat


async def set_chat_topic(session: AsyncSession, chat_id: int, topic_id: int | None) -> None:
    chat = await require_chat(session, chat_id)
    chat.topic_id = topic_id
    await session.flush()


async def get_effective_settings(session: AsyncSession, chat_id: int) -> EffectiveChatSettings:
    cfg = get_config()
    chat = await require_chat(session, chat_id)
    return EffectiveChatSettings(
        hashtag=chat.hashtag or cfg.default_hashtag,
        reaction_emoji=chat.reaction_emoji or cfg.default_reaction_emoji,
        topic_id=chat.topic_id,
    )


async def sync_admins_from_telegram(
    session: AsyncSession, bot: Bot, chat_id: int
) -> list[int]:
    """
    Replace cached admins for this chat with Telegram's current admin list.
    Returns telegram user ids that are admins.
    """
    admins = await bot.get_chat_administrators(chat_id)
    admin_ids: list[int] = []
    for member in admins:
        user = getattr(member, "user", None)
        if user is not None:
            admin_ids.append(user.id)

    # Replace cache
    await session.execute(delete(ChatAdmin).where(ChatAdmin.chat_id == chat_id))
    for telegram_user_id in admin_ids:
        session.add(ChatAdmin(chat_id=chat_id, telegram_user_id=telegram_user_id))
    await session.flush()
    return admin_ids


async def is_telegram_admin(bot: Bot, chat_id: int, telegram_user_id: int) -> bool:
    """
    Live-check against Telegram. Used for bootstrapping and hybrid fallback.
    """
    # get_chat_member is cheaper than get_chat_administrators for a single user
    member: ChatMember = await bot.get_chat_member(chat_id, telegram_user_id)
    return member.status in ("administrator", "creator")


async def is_chat_admin_hybrid(
    session: AsyncSession, bot: Bot, chat_id: int, telegram_user_id: int
) -> bool:
    """
    Hybrid check:
    - Fast path: DB cache
    - Fallback: if not found, live-check Telegram and if admin, sync cache.
    """
    stmt = select(ChatAdmin).where(
        ChatAdmin.chat_id == chat_id, ChatAdmin.telegram_user_id == telegram_user_id
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        return True

    # Live fallback
    if await is_telegram_admin(bot, chat_id, telegram_user_id):
        await sync_admins_from_telegram(session, bot, chat_id)
        return True
    return False

