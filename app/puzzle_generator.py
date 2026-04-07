from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Tag, Word, WordTag


class PuzzleGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Group:
    tag: Tag
    words: list[Word]


def _tag_ids_with_enough_words(session: Session, min_count: int) -> list[int]:
    stmt = (
        select(WordTag.tag_id, func.count(WordTag.word_id))
        .group_by(WordTag.tag_id)
        .having(func.count(WordTag.word_id) >= min_count)
    )
    rows = session.execute(stmt).all()
    return [row[0] for row in rows]


def _words_for_tag(session: Session, tag_id: int) -> list[Word]:
    stmt = select(Word).join(Word.tags).where(Tag.id == tag_id)
    return list(session.scalars(stmt).unique().all())


def _try_build_disjoint_groups(
    session: Session,
    tag_ids: list[int],
    min_per_tag: int,
) -> list[_Group] | None:
    """Pick 4 words per tag with pairwise disjoint words. Returns None if this ordering fails."""
    used: set[int] = set()
    groups: list[_Group] = []
    for tag_id in tag_ids:
        candidates = [
            w
            for w in _words_for_tag(session, tag_id)
            if w.id not in used
        ]
        if len(candidates) < min_per_tag:
            return None
        picked = random.sample(candidates, min_per_tag)
        used.update(w.id for w in picked)
        tag = session.get(Tag, tag_id)
        if tag is None:
            return None
        groups.append(_Group(tag=tag, words=picked))
    return groups


def generate_disjoint_puzzle(session: Session, difficulty: int = 0) -> tuple[str, list[str], list[int], list[_Group]]:
    """
    difficulty=0: four disjoint groups of four words (no word reused across groups).

    Higher difficulties may relax constraints later.
    """
    if difficulty != 0:
        raise ValueError("Only difficulty=0 is implemented")

    min_count = settings.min_words_per_tag
    eligible = _tag_ids_with_enough_words(session, min_count)
    if len(eligible) < 4:
        raise PuzzleGenerationError(
            f"Need at least 4 tags with {min_count}+ words each; found {len(eligible)}"
        )

    max_attempts = settings.puzzle_max_attempts
    for _ in range(max_attempts):
        chosen_tags = random.sample(eligible, 4)
        tag_order = chosen_tags[:]
        random.shuffle(tag_order)
        groups = _try_build_disjoint_groups(session, tag_order, min_count)
        if groups is not None:
            puzzle_id = str(uuid.uuid4())
            flat: list[Word] = []
            for g in groups:
                flat.extend(g.words)
            random.shuffle(flat)
            words_text = [w.text for w in flat]
            word_ids = [w.id for w in flat]
            return puzzle_id, words_text, word_ids, groups

    raise PuzzleGenerationError(
        "Could not generate a disjoint puzzle; try adding words/tags or increasing puzzle_max_attempts"
    )
