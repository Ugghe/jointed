from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Word(Base):
    __tablename__ = "words"

    word_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(Text, unique=True, index=True)
    part_of_speech: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency_tier: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_proper: Mapped[bool] = mapped_column(Boolean, default=False)
    date_added: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    word_categories: Mapped[list["WordCategory"]] = relationship(
        back_populates="word", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(Text, unique=True, index=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    obscurity_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_tricky: Mapped[bool] = mapped_column(Boolean, default=False)
    date_added: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    word_categories: Mapped[list["WordCategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class WordCategory(Base):
    __tablename__ = "word_category"
    __table_args__ = (
        UniqueConstraint("word_id", "category_id", name="uq_word_category_pair"),
    )

    wc_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.word_id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.category_id", ondelete="CASCADE"), index=True
    )
    difficulty: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    abstraction_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    connection_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_added: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    word: Mapped["Word"] = relationship(back_populates="word_categories")
    category: Mapped["Category"] = relationship(back_populates="word_categories")


class Puzzle(Base):
    __tablename__ = "puzzles"

    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="draft")
    date_created: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    date_published: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    puzzle_categories: Mapped[list["PuzzleCategory"]] = relationship(
        back_populates="puzzle", cascade="all, delete-orphan"
    )


class PuzzleCategory(Base):
    __tablename__ = "puzzle_categories"
    __table_args__ = (
        UniqueConstraint("puzzle_id", "category_id", name="uq_puzzle_category"),
    )

    pc_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("puzzles.puzzle_id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.category_id"))
    display_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    slot_color: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    puzzle: Mapped["Puzzle"] = relationship(back_populates="puzzle_categories")
    category: Mapped["Category"] = relationship()


class PuzzleWord(Base):
    __tablename__ = "puzzle_words"
    __table_args__ = (
        PrimaryKeyConstraint("puzzle_id", "word_id"),
        ForeignKeyConstraint(
            ["puzzle_id", "category_id"],
            ["puzzle_categories.puzzle_id", "puzzle_categories.category_id"],
            ondelete="CASCADE",
        ),
    )

    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("puzzles.puzzle_id", ondelete="CASCADE"), index=True
    )
    word_id: Mapped[int] = mapped_column(Integer, ForeignKey("words.word_id"))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.category_id"))
