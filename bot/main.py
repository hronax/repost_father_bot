import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    MessageReactionHandler,
    filters,
)

from bot.config import get_config
from bot.handlers.commands import (
    cleartopic_command,
    leaderboard_command,
    settopic_command,
    setweight_command,
    setup_command,
    stats_command,
    syncadmins_command,
)
from bot.handlers.message import handle_hashtag_message
from bot.handlers.reaction import handle_reaction
from db.database import close_db, init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database after application starts."""
    await init_db()
    logger.info("Database initialized")


async def post_shutdown(application: Application) -> None:
    """Clean up database connections."""
    await close_db()
    logger.info("Database connections closed")


def main() -> None:
    config = get_config()

    # Build application
    application = (
        Application.builder()
        .token(config.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Add command handlers
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("setweight", setweight_command))
    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(CommandHandler("syncadmins", syncadmins_command))
    application.add_handler(CommandHandler("settopic", settopic_command))
    application.add_handler(CommandHandler("cleartopic", cleartopic_command))

    # Add message handler for hashtag detection
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hashtag_message)
    )

    # Add reaction handler
    application.add_handler(MessageReactionHandler(handle_reaction))

    # Run the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=["message", "message_reaction"])


if __name__ == "__main__":
    main()
