import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.chat_service import (
    create_or_update_chat,
    is_chat_admin_hybrid,
    is_telegram_admin,
    require_chat,
    set_chat_topic,
    sync_admins_from_telegram,
)
from bot.services.stats_service import get_leaderboard, get_user_stats
from bot.services.user_service import (
    get_or_create_chat_user,
    get_user_by_username,
    set_chat_user_weight,
)
from db.database import get_session

logger = logging.getLogger(__name__)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - sends stats via DM."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Please run /stats in the group chat you want stats for."
        )
        return

    telegram_user = update.message.from_user
    chat_id = update.effective_chat.id

    async with get_session() as session:
        try:
            await require_chat(session, chat_id)
        except Exception:
            await update.message.reply_text(
                "This chat is not set up yet. Ask a chat admin to run /setup."
            )
            return

        user, _chat_user = await get_or_create_chat_user(
            session, chat_id, telegram_user.id, telegram_user.username
        )
        stats = await get_user_stats(session, chat_id, user)

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
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Please run /leaderboard in the group chat you want a leaderboard for."
        )
        return

    telegram_user = update.message.from_user
    chat_id = update.effective_chat.id

    async with get_session() as session:
        try:
            await require_chat(session, chat_id)
        except Exception:
            await update.message.reply_text(
                "This chat is not set up yet. Ask a chat admin to run /setup."
            )
            return

        leaderboard = await get_leaderboard(session, chat_id, limit=10)

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
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    telegram_user = update.message.from_user
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("Please run /setweight in the group chat.")
        return

    # Parse args:
    # - Reply to a user: /setweight 1.5
    # - Or: /setweight @username 1.5
    args = context.args or []
    target_telegram_id: int | None = None
    target_username: str | None = None
    weight_arg: str | None = None

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_telegram_id = update.message.reply_to_message.from_user.id
        if len(args) < 1:
            await update.message.reply_text("Usage (reply): /setweight 1.5")
            return
        weight_arg = args[0]
    else:
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /setweight @username weight\nExample: /setweight @john 1.5\n"
                "Tip: reply to a user's message to avoid username lookup."
            )
            return
        target_username = args[0]
        weight_arg = args[1]

    try:
        weight = float(weight_arg) if weight_arg is not None else 0.0
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
        try:
            await require_chat(session, chat_id)
        except Exception:
            message = "This chat is not set up yet. Run /setup first."
        else:
            if not await is_chat_admin_hybrid(session, context.bot, chat_id, telegram_user.id):
                message = "You don't have permission to use this command."
            else:
                if target_telegram_id is not None:
                    target_user, target_chat_user = await get_or_create_chat_user(
                        session, chat_id, target_telegram_id, None
                    )
                    await set_chat_user_weight(session, target_chat_user, weight)
                    display = (
                        f"@{target_user.username}"
                        if target_user.username
                        else str(target_user.telegram_id)
                    )
                    message = f"Set weight for {display} to {weight:.1f}x (this chat only)"
                else:
                    target_user = await get_user_by_username(session, target_username or "")
                    if not target_user:
                        message = (
                            f"User {target_username} not found. "
                            "They must interact with the bot first, or you can reply to their message."
                        )
                    else:
                        _u, target_chat_user = await get_or_create_chat_user(
                            session, chat_id, target_user.telegram_id, target_user.username
                        )
                        await set_chat_user_weight(session, target_chat_user, weight)
                        message = f"Set weight for {target_username} to {weight:.1f}x (this chat only)"

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


async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable the bot in this chat and sync admins from Telegram."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text("Run /setup in the group chat.")
        return

    chat_id = update.effective_chat.id
    chat_title = getattr(update.effective_chat, "title", None)
    topic_id = getattr(update.message, "message_thread_id", None)
    telegram_user = update.message.from_user

    # Only Telegram chat admins can bootstrap
    if not await is_telegram_admin(context.bot, chat_id, telegram_user.id):
        await update.message.reply_text("Only Telegram chat admins can run /setup.")
        return

    async with get_session() as session:
        await create_or_update_chat(session, chat_id, chat_title, topic_id=topic_id)
        await sync_admins_from_telegram(session, context.bot, chat_id)

    msg = "Setup complete. Admins synced."
    if topic_id is not None:
        msg += (
            f" Topic restriction set to this topic ({topic_id}). "
            "Use /cleartopic to allow all topics."
        )
    await update.message.reply_text(msg)


async def syncadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-sync cached admin list for this chat from Telegram."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text("Run /syncadmins in the group chat.")
        return

    chat_id = update.effective_chat.id
    telegram_user = update.message.from_user

    async with get_session() as session:
        try:
            await require_chat(session, chat_id)
        except Exception:
            await update.message.reply_text("This chat is not set up yet. Run /setup first.")
            return

        if not await is_chat_admin_hybrid(session, context.bot, chat_id, telegram_user.id):
            await update.message.reply_text("You don't have permission to use this command.")
            return

        await sync_admins_from_telegram(session, context.bot, chat_id)

    await update.message.reply_text("Admins synced from Telegram.")


async def settopic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a single allowed TOPIC_ID for this chat (admin only)."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text("Run /settopic in the group chat.")
        return

    chat_id = update.effective_chat.id
    telegram_user = update.message.from_user

    if not context.args:
        await update.message.reply_text("Usage: /settopic <topic_id>")
        return

    try:
        topic_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("topic_id must be a number.")
        return

    async with get_session() as session:
        try:
            await require_chat(session, chat_id)
        except Exception:
            await update.message.reply_text("This chat is not set up yet. Run /setup first.")
            return

        if not await is_chat_admin_hybrid(session, context.bot, chat_id, telegram_user.id):
            await update.message.reply_text("You don't have permission to use this command.")
            return

        await set_chat_topic(session, chat_id, topic_id)

    await update.message.reply_text(f"Topic restriction set to {topic_id}.")


async def cleartopic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear topic restriction (admin only)."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text("Run /cleartopic in the group chat.")
        return

    chat_id = update.effective_chat.id
    telegram_user = update.message.from_user

    async with get_session() as session:
        try:
            await require_chat(session, chat_id)
        except Exception:
            await update.message.reply_text("This chat is not set up yet. Run /setup first.")
            return

        if not await is_chat_admin_hybrid(session, context.bot, chat_id, telegram_user.id):
            await update.message.reply_text("You don't have permission to use this command.")
            return

        await set_chat_topic(session, chat_id, None)

    await update.message.reply_text("Topic restriction cleared (all topics allowed).")
