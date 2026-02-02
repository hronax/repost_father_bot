import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import get_config
from bot.services.post_service import add_reaction, get_post_by_message
from bot.services.user_service import get_or_create_user, update_user_points
from db.database import get_session

logger = logging.getLogger(__name__)


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message_reaction:
        return

    config = get_config()
    reaction_update = update.message_reaction

    # Get the new reactions
    new_reactions = reaction_update.new_reaction or []

    # Check if the configured reaction emoji is in the new reactions
    has_target_emoji = False
    for reaction in new_reactions:
        # Handle both regular emoji and custom emoji
        emoji = getattr(reaction, "emoji", None)
        if emoji == config.reaction_emoji:
            has_target_emoji = True
            break

    if not has_target_emoji:
        return

    # Get reactor info
    reactor_user = reaction_update.user
    if not reactor_user:
        return

    message_id = reaction_update.message_id
    chat_id = reaction_update.chat.id

    async with get_session() as session:
        # Find the post
        post = await get_post_by_message(session, message_id, chat_id)
        if not post:
            logger.debug(f"Post not found for message {message_id} in chat {chat_id}")
            return

        # Get or create reactor user
        reactor = await get_or_create_user(
            session, reactor_user.id, reactor_user.username
        )

        # Don't allow self-reactions
        if reactor.telegram_id == post.user.telegram_id:
            logger.debug("Ignoring self-reaction")
            return

        # Try to add the reaction
        reaction = await add_reaction(session, post, reactor)
        if reaction is None:
            logger.debug("Reaction already exists")
            return

        # Update points:
        # Reactor gains points based on post owner's weight (they did a repost)
        # Post owner loses points based on reactor's weight (they owe a repost)
        post_owner = post.user

        reactor_points_gain = 1.0 * post_owner.weight
        owner_points_loss = 1.0 * reactor.weight

        await update_user_points(session, reactor, reactor_points_gain)
        await update_user_points(session, post_owner, -owner_points_loss)

        logger.info(
            f"Reaction recorded: user {reactor.telegram_id} reposted for user {post_owner.telegram_id}. "
            f"Reactor gained {reactor_points_gain:.1f}, owner lost {owner_points_loss:.1f}"
        )
