import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str
    database_url: str
    default_hashtag: str
    default_reaction_emoji: str

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

        default_hashtag = os.environ.get("HASHTAG", "#repost")
        default_reaction_emoji = os.environ.get("REACTION_EMOJI", "👍")

        return cls(
            bot_token=bot_token,
            database_url=database_url,
            default_hashtag=default_hashtag,
            default_reaction_emoji=default_reaction_emoji,
        )


config = Config.from_env() if os.environ.get("BOT_TOKEN") else None


def get_config() -> Config:
    global config
    if config is None:
        config = Config.from_env()
    return config
