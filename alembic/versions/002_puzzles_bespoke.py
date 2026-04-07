"""bespoke puzzles

Revision ID: 002
Revises: 001
Create Date: 2026-04-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "puzzles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "puzzle_group_items",
        sa.Column("puzzle_id", sa.String(length=36), nullable=False),
        sa.Column("group_index", sa.SmallInteger(), nullable=False),
        sa.Column("position_in_group", sa.SmallInteger(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"]),
        sa.PrimaryKeyConstraint(
            "puzzle_id", "group_index", "position_in_group", name="pk_puzzle_group_cell"
        ),
    )
    op.create_index(
        "ix_puzzle_group_items_puzzle_id",
        "puzzle_group_items",
        ["puzzle_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_puzzle_group_items_puzzle_id", table_name="puzzle_group_items")
    op.drop_table("puzzle_group_items")
    op.drop_table("puzzles")
