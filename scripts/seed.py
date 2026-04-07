"""
Load sample words and categories. Run from repo root:
  python scripts/seed.py

Skips loading when the database already has at least one word (deploy / promote safety).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.lexicon import get_or_create_category, get_or_create_word, link_word_category  # noqa: E402
from app.models import Word  # noqa: E402


def _run_migrations() -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        check=True,
    )


def _seed(
    session: Session,
    tag_defs: list[tuple[str, str, str]],
    word_map: dict[str, list[str]],
) -> None:
    slug_to_category = {}
    for _slug, label, kind in tag_defs:
        cat, _ = get_or_create_category(session, label, kind=kind)
        slug_to_category[_slug] = cat

    for text, slugs in word_map.items():
        word, _ = get_or_create_word(session, text)
        for slug in slugs:
            cat = slug_to_category[slug]
            link_word_category(session, word, cat)


def main() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    _run_migrations()

    tag_defs: list[tuple[str, str, str]] = [
        ("fish", "Fish", "semantic"),
        ("instrument", "Instrument", "semantic"),
        ("color", "Color", "semantic"),
        ("fruit", "Fruit", "semantic"),
        ("sport", "Sport", "semantic"),
        ("letters_eq_4", "Letters = 4", "structural"),
        ("syllables_eq_1", "Syllables = 1", "structural"),
    ]

    word_map: dict[str, list[str]] = {
        "bass": ["fish", "instrument", "letters_eq_4", "syllables_eq_1"],
        "salmon": ["fish"],
        "trout": ["fish", "syllables_eq_1"],
        "carp": ["fish", "letters_eq_4"],
        "guitar": ["instrument"],
        "piano": ["instrument", "syllables_eq_1"],
        "violin": ["instrument"],
        "drum": ["instrument", "letters_eq_4", "syllables_eq_1"],
        "red": ["color", "syllables_eq_1"],
        "blue": ["color", "letters_eq_4", "syllables_eq_1"],
        "green": ["color", "syllables_eq_1"],
        "yellow": ["color"],
        "apple": ["fruit", "syllables_eq_1"],
        "pear": ["fruit", "letters_eq_4", "syllables_eq_1"],
        "grape": ["fruit", "syllables_eq_1"],
        "plum": ["fruit", "letters_eq_4", "syllables_eq_1"],
        "golf": ["sport", "letters_eq_4", "syllables_eq_1"],
        "tennis": ["sport"],
        "rugby": ["sport"],
        "polo": ["sport", "letters_eq_4", "syllables_eq_1"],
    }

    with SessionLocal() as session:
        n = session.scalar(select(func.count()).select_from(Word))
        if n and n > 0:
            print("Database already contains words; skipping seed.")
            return
        _seed(session, tag_defs, word_map)
        session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    main()
