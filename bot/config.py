import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str
    database_url: str
    hashtag: str
    reaction_emoji: str
    admin_ids: list[int]
    topic_id: int | None

    @classmethod
    def from_env(cls) -> "Config":
        bot_token = os.environ.get("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Handle Railway's postgres:// vs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        hashtag = os.environ.get("HASHTAG", "#repost")
        reaction_emoji = os.environ.get("REACTION_EMOJI", "👍")

        admin_ids_str = os.environ.get("ADMIN_IDS", "")
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

        topic_id_str = os.environ.get("TOPIC_ID")
        topic_id = int(topic_id_str) if topic_id_str else None

        return cls(
            bot_token=bot_token,
            database_url=database_url,
            hashtag=hashtag,
            reaction_emoji=reaction_emoji,
            admin_ids=admin_ids,
            topic_id=topic_id,
        )


config = Config.from_env() if os.environ.get("BOT_TOKEN") else None


def get_config() -> Config:
    global config
    if config is None:
        config = Config.from_env()
    return config
