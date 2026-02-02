import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.chat_service import get_effective_settings, require_chat
from bot.services.post_service import create_post
from bot.services.stats_service import get_user_stats
from bot.services.user_service import get_or_create_chat_user
from db.database import get_session

logger = logging.getLogger(__name__)


async def handle_hashtag_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message:
        return

    message = update.message
    content = (message.text or message.caption or "").strip()
    if not content:
        return

    chat_id = message.chat_id

    telegram_user = message.from_user
    if not telegram_user:
        return

    async with get_session() as session:
        # Require chat setup; if not set up, ignore silently (avoid spam).
        try:
            await require_chat(session, chat_id)
        except Exception:
            return

        settings = await get_effective_settings(session, chat_id)

        # Check if message contains the hashtag
        if settings.hashtag.lower() not in content.lower():
            return

        # Check if we're in the correct topic (if configured)
        if settings.topic_id is not None:
            message_topic_id = getattr(message, "message_thread_id", None)
            if message_topic_id != settings.topic_id:
                return

        # Get or create user
        user, _chat_user = await get_or_create_chat_user(
            session, chat_id, telegram_user.id, telegram_user.username
        )

        # Create the post
        await create_post(
            session,
            user,
            message.message_id,
            chat_id,
            getattr(message, "message_thread_id", None),
        )

        # Get user stats
        stats = await get_user_stats(session, chat_id, user)

        # Format username for display
        display_name = f"@{telegram_user.username}" if telegram_user.username else telegram_user.first_name

        # Reply publicly with stats
        stats_message = (
            f"{display_name} stats:\n"
            f"Reposts made: {stats.reposts_made}\n"
            f"Reposts received: {stats.reposts_received}\n"
            f"Points: {stats.points:.1f}"
        )

        await message.reply_text(stats_message)
        logger.info(f"Tracked post from user {telegram_user.id}")
