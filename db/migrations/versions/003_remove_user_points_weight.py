"""Remove weight and points from users table (now per-chat in chat_users)

Revision ID: 003_remove_user_points_weight
Revises: 002_multi_chat
Create Date: 2026-02-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_remove_user_points_weight"
down_revision: Union[str, None] = "002_multi_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "weight")
    op.drop_column("users", "points")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "points",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
    )
