import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import get_config
from bot.services.stats_service import get_leaderboard, get_user_stats
from bot.services.user_service import (
    get_or_create_user,
    get_user_by_username,
    set_user_weight,
)
from db.database import get_session

logger = logging.getLogger(__name__)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - sends stats via DM."""
    if not update.message or not update.message.from_user:
        return

    telegram_user = update.message.from_user

    async with get_session() as session:
        user = await get_or_create_user(
            session, telegram_user.id, telegram_user.username
        )
        stats = await get_user_stats(session, user)

        stats_message = (
            f"Your stats:\n\n"
            f"Reposts made: {stats.reposts_made}\n"
            f"Reposts received: {stats.reposts_received}\n"
            f"Points: {stats.points:.1f}\n"
            f"Your weight: {stats.weight:.1f}x"
        )

    # Send via DM
    try:
        await context.bot.send_message(chat_id=telegram_user.id, text=stats_message)
        # Delete the command message from group to keep it clean
        if update.message.chat.type != "private":
            try:
                await update.message.delete()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to send DM to user {telegram_user.id}: {e}")
        # If DM fails, notify in chat
        await update.message.reply_text(
            "Please start a private chat with me first to receive your stats."
        )


async def leaderboard_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /leaderboard command - sends leaderboard via DM."""
    if not update.message or not update.message.from_user:
        return

    telegram_user = update.message.from_user

    async with get_session() as session:
        leaderboard = await get_leaderboard(session, limit=10)

        if not leaderboard:
            message = "No users in leaderboard yet."
        else:
            lines = ["Leaderboard (Top 10):\n"]
            for i, (user, stats) in enumerate(leaderboard, 1):
                display_name = f"@{user.username}" if user.username else f"User {user.telegram_id}"
                medal = ""
                if i == 1:
                    medal = " "
                elif i == 2:
                    medal = " "
                elif i == 3:
                    medal = " "
                lines.append(
                    f"{i}.{medal} {display_name}: {stats.points:.1f} pts "
                    f"({stats.reposts_made} made, {stats.reposts_received} received)"
                )
            message = "\n".join(lines)

    # Send via DM
    try:
        await context.bot.send_message(chat_id=telegram_user.id, text=message)
        # Delete the command message from group to keep it clean
        if update.message.chat.type != "private":
            try:
                await update.message.delete()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to send DM to user {telegram_user.id}: {e}")
        await update.message.reply_text(
            "Please start a private chat with me first to receive the leaderboard."
        )


async def setweight_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /setweight command - admin only, responds via DM."""
    if not update.message or not update.message.from_user:
        return

    config = get_config()
    telegram_user = update.message.from_user

    # Check if user is admin
    if telegram_user.id not in config.admin_ids:
        try:
            await context.bot.send_message(
                chat_id=telegram_user.id,
                text="You don't have permission to use this command.",
            )
        except Exception:
            await update.message.reply_text(
                "You don't have permission to use this command."
            )
        return

    # Parse arguments: /setweight @username 1.5
    args = context.args
    if not args or len(args) < 2:
        try:
            await context.bot.send_message(
                chat_id=telegram_user.id,
                text="Usage: /setweight @username weight\nExample: /setweight @john 1.5",
            )
        except Exception:
            await update.message.reply_text(
                "Usage: /setweight @username weight\nExample: /setweight @john 1.5"
            )
        return

    username = args[0]
    try:
        weight = float(args[1])
    except ValueError:
        try:
            await context.bot.send_message(
                chat_id=telegram_user.id, text="Weight must be a number."
            )
        except Exception:
            await update.message.reply_text("Weight must be a number.")
        return

    if weight <= 0:
        try:
            await context.bot.send_message(
                chat_id=telegram_user.id, text="Weight must be positive."
            )
        except Exception:
            await update.message.reply_text("Weight must be positive.")
        return

    async with get_session() as session:
        target_user = await get_user_by_username(session, username)
        if not target_user:
            message = f"User {username} not found."
        else:
            await set_user_weight(session, target_user, weight)
            message = f"Set weight for {username} to {weight:.1f}x"

    # Send confirmation via DM
    try:
        await context.bot.send_message(chat_id=telegram_user.id, text=message)
        # Delete the command message from group to keep it clean
        if update.message.chat.type != "private":
            try:
                await update.message.delete()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to send DM to admin {telegram_user.id}: {e}")
        await update.message.reply_text(message)
