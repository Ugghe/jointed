"""Shared word/tag upsert helpers (bespoke puzzles, CSV import, etc.)."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tag, Word


class LexiconError(ValueError):
    pass


def slugify_label(label: str) -> str:
    s = label.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "category"
    return s[:128]


def get_or_create_tag(session: Session, label: str, kind: str = "semantic") -> tuple[Tag, bool]:
    base = slugify_label(label)
    slug = base
    n = 2
    while True:
        existing = session.scalar(select(Tag).where(Tag.slug == slug))
        if existing is None:
            t = Tag(slug=slug, label=label.strip(), kind=kind)
            session.add(t)
            session.flush()
            return t, True
        if existing.label.strip() == label.strip():
            return existing, False
        slug = f"{base}_{n}"
        n += 1
        if len(slug) > 128:
            slug = f"{base[:100]}_{n}"


def get_or_create_word(session: Session, text: str) -> tuple[Word, bool]:
    cleaned = text.strip()
    if not cleaned:
        raise LexiconError("Empty word")
    w = session.scalar(select(Word).where(Word.text == cleaned))
    if w is None:
        w = Word(text=cleaned)
        session.add(w)
        session.flush()
        return w, True
    return w, False


def link_word_tag(session: Session, word: Word, tag: Tag) -> bool:
    if tag not in word.tags:
        word.tags.append(tag)
        return True
    return False
