"""graph schema (words, categories, word_category, puzzles, puzzle_categories, puzzle_words)

Revision ID: 003
Revises: 002
Create Date: 2026-04-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    for tbl in ("puzzle_group_items", "puzzles", "word_tags", "words", "tags"):
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{tbl}"'))

    op.create_table(
        "words",
        sa.Column("word_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("word", sa.Text(), nullable=False),
        sa.Column("part_of_speech", sa.Text(), nullable=True),
        sa.Column("frequency_tier", sa.SmallInteger(), nullable=True),
        sa.Column("is_proper", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "date_added",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("word_id"),
    )
    op.create_index(op.f("ix_words_word"), "words", ["word"], unique=True)

    op.create_table(
        "categories",
        sa.Column("category_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("obscurity_score", sa.SmallInteger(), nullable=True),
        sa.Column("is_tricky", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "date_added",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("category_id"),
    )
    op.create_index(op.f("ix_categories_label"), "categories", ["label"], unique=True)

    op.create_table(
        "word_category",
        sa.Column("wc_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=True),
        sa.Column("abstraction_level", sa.SmallInteger(), nullable=True),
        sa.Column("connection_type", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "date_added",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["word_id"], ["words.word_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.category_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("wc_id"),
        sa.UniqueConstraint("word_id", "category_id", name="uq_word_category_pair"),
    )
    op.create_index(op.f("ix_word_category_word_id"), "word_category", ["word_id"])
    op.create_index(op.f("ix_word_category_category_id"), "word_category", ["category_id"])
    op.create_index(
        op.f("ix_word_category_connection_type"), "word_category", ["connection_type"]
    )

    op.create_table(
        "puzzles",
        sa.Column("puzzle_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column(
            "date_created",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("puzzle_id"),
    )

    op.create_table(
        "puzzle_categories",
        sa.Column("pc_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("puzzle_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("display_label", sa.Text(), nullable=True),
        sa.Column("slot_color", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.puzzle_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.category_id"]),
        sa.PrimaryKeyConstraint("pc_id"),
        sa.UniqueConstraint("puzzle_id", "category_id", name="uq_puzzle_category"),
    )
    op.create_index(
        op.f("ix_puzzle_categories_puzzle_id"), "puzzle_categories", ["puzzle_id"]
    )

    op.create_table(
        "puzzle_words",
        sa.Column("puzzle_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.puzzle_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.word_id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.category_id"]),
        sa.ForeignKeyConstraint(
            ["puzzle_id", "category_id"],
            ["puzzle_categories.puzzle_id", "puzzle_categories.category_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("puzzle_id", "word_id"),
    )
    op.create_index(op.f("ix_puzzle_words_puzzle_id"), "puzzle_words", ["puzzle_id"])
    op.create_index(op.f("ix_puzzle_words_word_id"), "puzzle_words", ["word_id"])

    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE INDEX idx_words_fts ON words USING GIN (to_tsvector('english', word))"
            )
        )
        # JSON columns need an explicit jsonb cast for GIN (no default opclass on type json).
        op.execute(
            sa.text(
                "CREATE INDEX idx_words_metadata ON words USING GIN ((metadata::jsonb))"
            )
        )
        op.execute(
            sa.text(
                "CREATE INDEX idx_categories_metadata ON categories USING GIN ((metadata::jsonb))"
            )
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade to legacy tag/word_tags schema is not supported.")
