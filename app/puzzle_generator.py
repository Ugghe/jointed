from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Category, Word, WordCategory


class PuzzleGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Group:
    category: Category
    words: list[Word]


def _category_ids_with_enough_words(session: Session, min_count: int) -> list[int]:
    stmt = (
        select(WordCategory.category_id, func.count(WordCategory.wc_id))
        .group_by(WordCategory.category_id)
        .having(func.count(WordCategory.wc_id) >= min_count)
    )
    rows = session.execute(stmt).all()
    return [row[0] for row in rows]


def _words_for_category(session: Session, category_id: int) -> list[Word]:
    stmt = (
        select(Word)
        .join(WordCategory, WordCategory.word_id == Word.word_id)
        .where(WordCategory.category_id == category_id)
    )
    return list(session.scalars(stmt).unique().all())


def _try_build_disjoint_groups(
    session: Session,
    category_ids: list[int],
    min_per_category: int,
) -> list[_Group] | None:
    used: set[int] = set()
    groups: list[_Group] = []
    for cid in category_ids:
        candidates = [w for w in _words_for_category(session, cid) if w.word_id not in used]
        if len(candidates) < min_per_category:
            return None
        picked = random.sample(candidates, min_per_category)
        used.update(w.word_id for w in picked)
        cat = session.get(Category, cid)
        if cat is None:
            return None
        groups.append(_Group(category=cat, words=picked))
    return groups


def generate_disjoint_puzzle(
    session: Session, difficulty: int = 0
) -> tuple[str, list[str], list[int], list[_Group]]:
    """
    difficulty=0: four disjoint groups of four words (no word reused across groups).
    Does not persist a puzzle row; returns an ephemeral puzzle_id for the client.
    """
    if difficulty != 0:
        raise ValueError("Only difficulty=0 is implemented")

    min_count = settings.min_words_per_tag
    eligible = _category_ids_with_enough_words(session, min_count)
    if len(eligible) < 4:
        raise PuzzleGenerationError(
            f"Need at least 4 categories with {min_count}+ words each; found {len(eligible)}"
        )

    max_attempts = settings.puzzle_max_attempts
    for _ in range(max_attempts):
        chosen = random.sample(eligible, 4)
        order = chosen[:]
        random.shuffle(order)
        groups = _try_build_disjoint_groups(session, order, min_count)
        if groups is not None:
            puzzle_id = str(uuid.uuid4())
            flat: list[Word] = []
            for g in groups:
                flat.extend(g.words)
            random.shuffle(flat)
            words_text = [w.word for w in flat]
            word_ids = [w.word_id for w in flat]
            return puzzle_id, words_text, word_ids, groups

    raise PuzzleGenerationError(
        "Could not generate a disjoint puzzle; try adding word–category links or increasing puzzle_max_attempts"
    )
