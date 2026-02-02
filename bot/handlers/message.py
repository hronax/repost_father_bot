import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import get_config
from bot.services.post_service import create_post
from bot.services.stats_service import get_user_stats
from bot.services.user_service import get_or_create_user
from db.database import get_session

logger = logging.getLogger(__name__)


async def handle_hashtag_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.message.text:
        return

    config = get_config()
    message = update.message

    # Check if message contains the hashtag
    if config.hashtag.lower() not in message.text.lower():
        return

    # Check if we're in the correct topic (if configured)
    if config.topic_id is not None:
        message_topic_id = getattr(message, "message_thread_id", None)
        if message_topic_id != config.topic_id:
            return

    telegram_user = message.from_user
    if not telegram_user:
        return

    async with get_session() as session:
        # Get or create user
        user = await get_or_create_user(
            session, telegram_user.id, telegram_user.username
        )

        # Create the post
        await create_post(
            session,
            user,
            message.message_id,
            message.chat_id,
            getattr(message, "message_thread_id", None),
        )

        # Get user stats
        stats = await get_user_stats(session, user)

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
