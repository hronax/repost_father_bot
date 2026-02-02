import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.chat_service import get_effective_settings, require_chat
from bot.services.post_service import add_reaction, get_post_by_message
from bot.services.user_service import (
    get_or_create_chat_user,
    update_chat_user_points,
)
from db.database import get_session

logger = logging.getLogger(__name__)


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message_reaction:
        return

    reaction_update = update.message_reaction

    # Get the new reactions
    new_reactions = reaction_update.new_reaction or []

    # Get reactor info
    reactor_user = reaction_update.user
    if not reactor_user:
        return

    message_id = reaction_update.message_id
    chat_id = reaction_update.chat.id

    async with get_session() as session:
        # Require chat setup; if not set up, ignore silently (avoid spam).
        try:
            await require_chat(session, chat_id)
        except Exception:
            return

        settings = await get_effective_settings(session, chat_id)

        # Check if the configured reaction emoji is in the new reactions
        has_target_emoji = False
        for reaction in new_reactions:
            # Handle both regular emoji and custom emoji
            emoji = getattr(reaction, "emoji", None)
            if emoji == settings.reaction_emoji:
                has_target_emoji = True
                break

        if not has_target_emoji:
            return

        # Find the post
        post = await get_post_by_message(session, message_id, chat_id)
        if not post:
            logger.debug(f"Post not found for message {message_id} in chat {chat_id}")
            return

        # Get or create reactor user
        reactor_user_row, reactor_chat_user = await get_or_create_chat_user(
            session, chat_id, reactor_user.id, reactor_user.username
        )

        # Don't allow self-reactions
        if reactor_user_row.telegram_id == post.user.telegram_id:
            logger.debug("Ignoring self-reaction")
            return

        # Try to add the reaction
        reaction = await add_reaction(session, post, reactor_user_row)
        if reaction is None:
            logger.debug("Reaction already exists")
            return

        # Update points:
        # Reactor gains points based on post owner's weight (they did a repost)
        # Post owner loses points based on reactor's weight (they owe a repost)
        post_owner_user_row, post_owner_chat_user = await get_or_create_chat_user(
            session, chat_id, post.user.telegram_id, post.user.username
        )

        reactor_points_gain = 1.0 * post_owner_chat_user.weight
        owner_points_loss = 1.0 * reactor_chat_user.weight

        await update_chat_user_points(session, reactor_chat_user, reactor_points_gain)
        await update_chat_user_points(session, post_owner_chat_user, -owner_points_loss)

        logger.info(
            f"Reaction recorded: user {reactor_user_row.telegram_id} reposted for user {post_owner_user_row.telegram_id}. "
            f"Reactor gained {reactor_points_gain:.1f}, owner lost {owner_points_loss:.1f}"
        )
