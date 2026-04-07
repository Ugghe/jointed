"""Shared word/category upsert helpers (bespoke puzzles, CSV import, etc.)."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Word, WordCategory
from app.normalize import validate_category_label_input, validate_word_input

CANONICAL_CONNECTION_TYPES = frozenset(
    {
        "literal",
        "categorical",
        "associative",
        "metaphorical",
        "wordplay",
        "cultural",
    }
)


class LexiconError(ValueError):
    pass


def slugify_label(label: str) -> str:
    """URL-ish slug for API compatibility (derived from stored label text)."""
    s = label.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "category"
    return s[:128]


def get_or_create_category(session: Session, raw_label: str, *, kind: str = "semantic") -> tuple[Category, bool]:
    normalized = validate_category_label_input(raw_label)
    existing = session.scalar(select(Category).where(Category.label == normalized))
    if existing is not None:
        return existing, False
    meta: dict = {"kind": kind}
    c = Category(label=normalized, metadata_=meta)
    session.add(c)
    session.flush()
    return c, True


def get_or_create_word(session: Session, raw_text: str) -> tuple[Word, bool]:
    normalized = validate_word_input(raw_text)
    existing = session.scalar(select(Word).where(Word.word == normalized))
    if existing is not None:
        return existing, False
    w = Word(word=normalized)
    session.add(w)
    session.flush()
    return w, True


def link_word_category(
    session: Session,
    word: Word,
    category: Category,
    *,
    difficulty: int | None = None,
    abstraction_level: int | None = None,
    connection_type: str | None = None,
    notes: str | None = None,
    metadata_extra: dict | None = None,
) -> bool:
    """Returns True if a new row was created."""
    existing = session.scalar(
        select(WordCategory).where(
            WordCategory.word_id == word.word_id,
            WordCategory.category_id == category.category_id,
        )
    )
    if existing is not None:
        return False
    if connection_type is not None and connection_type not in CANONICAL_CONNECTION_TYPES:
        raise LexiconError(f"Invalid connection_type: {connection_type!r}")
    meta = dict(metadata_extra) if metadata_extra else None
    wc = WordCategory(
        word_id=word.word_id,
        category_id=category.category_id,
        difficulty=difficulty,
        abstraction_level=abstraction_level,
        connection_type=connection_type,
        notes=notes,
        metadata_=meta,
    )
    session.add(wc)
    session.flush()
    return True
