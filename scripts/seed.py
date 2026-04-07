"""
Load sample words and tags. Run from repo root:
  python scripts/seed.py
Requires: pip install -e . && alembic upgrade head (or let this script upgrade).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import Tag, Word


def _ensure_path() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def _run_migrations() -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    _ensure_path()
    _run_migrations()

    # Tag definitions: slug, label, kind
    tag_defs: list[tuple[str, str, str]] = [
        ("fish", "Fish", "semantic"),
        ("instrument", "Instrument", "semantic"),
        ("color", "Color", "semantic"),
        ("fruit", "Fruit", "semantic"),
        ("sport", "Sport", "semantic"),
        ("letters_eq_4", "Letters = 4", "structural"),
        ("syllables_eq_1", "Syllables = 1", "structural"),
    ]

    # word_text -> list of tag slugs (structural tags are only attached where accurate)
    word_map: dict[str, list[str]] = {
        # Fish
        "bass": ["fish", "instrument", "letters_eq_4", "syllables_eq_1"],
        "salmon": ["fish"],
        "trout": ["fish", "syllables_eq_1"],
        "carp": ["fish", "letters_eq_4"],
        # Instruments
        "guitar": ["instrument"],
        "piano": ["instrument", "syllables_eq_1"],
        "violin": ["instrument"],
        "drum": ["instrument", "letters_eq_4", "syllables_eq_1"],
        # Colors
        "red": ["color", "syllables_eq_1"],
        "blue": ["color", "letters_eq_4", "syllables_eq_1"],
        "green": ["color", "syllables_eq_1"],
        "yellow": ["color"],
        # Fruit
        "apple": ["fruit", "syllables_eq_1"],
        "pear": ["fruit", "letters_eq_4", "syllables_eq_1"],
        "grape": ["fruit", "syllables_eq_1"],
        "plum": ["fruit", "letters_eq_4", "syllables_eq_1"],
        # Sports
        "golf": ["sport", "letters_eq_4", "syllables_eq_1"],
        "tennis": ["sport"],
        "rugby": ["sport"],
        "polo": ["sport", "letters_eq_4", "syllables_eq_1"],
    }

    with SessionLocal() as session:
        _seed(session, tag_defs, word_map)
        session.commit()
    print("Seed complete.")


def _seed(
    session: Session,
    tag_defs: list[tuple[str, str, str]],
    word_map: dict[str, list[str]],
) -> None:
    slug_to_tag: dict[str, Tag] = {}
    for slug, label, kind in tag_defs:
        existing = session.scalar(select(Tag).where(Tag.slug == slug))
        if existing:
            slug_to_tag[slug] = existing
        else:
            t = Tag(slug=slug, label=label, kind=kind)
            session.add(t)
            session.flush()
            slug_to_tag[slug] = t

    for text, slugs in word_map.items():
        w = session.scalar(select(Word).where(Word.text == text))
        if w is None:
            w = Word(text=text)
            session.add(w)
            session.flush()
        for slug in slugs:
            tag = slug_to_tag[slug]
            if tag not in w.tags:
                w.tags.append(tag)


if __name__ == "__main__":
    main()
