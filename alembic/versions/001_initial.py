"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_slug"), "tags", ["slug"], unique=True)

    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_words_text"), "words", ["text"], unique=True)

    op.create_table(
        "word_tags",
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.ForeignKeyConstraint(
            ["word_id"],
            ["words.id"],
        ),
        sa.PrimaryKeyConstraint("word_id", "tag_id"),
        sa.UniqueConstraint("word_id", "tag_id", name="uq_word_tag"),
    )


def downgrade() -> None:
    op.drop_table("word_tags")
    op.drop_index(op.f("ix_words_text"), table_name="words")
    op.drop_table("words")
    op.drop_index(op.f("ix_tags_slug"), table_name="tags")
    op.drop_table("tags")
