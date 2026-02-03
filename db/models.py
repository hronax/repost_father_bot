from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    # Telegram chat id (group/supergroup/channel) is globally unique, so we can use it
    # as the primary key to keep lookups simple and avoid surrogate ids.
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Per-chat settings (optional overrides; fall back to env defaults when NULL)
    hashtag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reaction_emoji: Mapped[str | None] = mapped_column(String(32), nullable=True)
    topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    admins: Mapped[list["ChatAdmin"]] = relationship(
        "ChatAdmin", back_populates="chat", cascade="all, delete-orphan"
    )
    users: Mapped[list["ChatUser"]] = relationship(
        "ChatUser", back_populates="chat", cascade="all, delete-orphan"
    )


class ChatAdmin(Base):
    __tablename__ = "chat_admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chats.telegram_chat_id"), nullable=False
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("chat_id", "telegram_user_id", name="uq_chat_admin"),
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="admins")


class ChatUser(Base):
    __tablename__ = "chat_users"

    # Composite PK ensures one stats row per user per chat.
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chats.telegram_chat_id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)

    # Points and weight are chat-scoped.
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="users")
    user: Mapped["User"] = relationship("User")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")
    reactions: Mapped[list["Reaction"]] = relationship(
        "Reaction", back_populates="reactor", foreign_keys="Reaction.reactor_user_id"
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("message_id", "chat_id", name="uq_post_message_chat"),
    )

    user: Mapped["User"] = relationship("User", back_populates="posts")
    reactions: Mapped[list["Reaction"]] = relationship(
        "Reaction", back_populates="post"
    )


class Reaction(Base):
    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    reactor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("post_id", "reactor_user_id", name="uq_reaction_post_reactor"),
    )

    post: Mapped["Post"] = relationship("Post", back_populates="reactions")
    reactor: Mapped["User"] = relationship(
        "User", back_populates="reactions", foreign_keys=[reactor_user_id]
    )
