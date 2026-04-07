from __future__ import annotations

import random
import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.lexicon import get_or_create_tag, get_or_create_word, link_word_tag
from app.models import Puzzle, PuzzleGroupItem, Tag, Word
from app.puzzle_generator import _Group
from app.schemas import PuzzleGroup, PuzzleResponse


class BespokePuzzleError(ValueError):
    pass


class CategoryInput(NamedTuple):
    label: str
    words: list[str]


def save_bespoke_puzzle(session: Session, categories: list[CategoryInput]) -> str:
    if len(categories) != 4:
        raise BespokePuzzleError("Need exactly 4 categories")
    seen_norm: set[str] = set()
    normalized_rows: list[tuple[int, int, Tag, Word]] = []

    for gi, cat in enumerate(categories):
        if len(cat.words) != 4:
            raise BespokePuzzleError(f"Category {gi + 1} must have exactly 4 words")
        tag, _ = get_or_create_tag(session, cat.label)
        for pi, wtext in enumerate(cat.words):
            word, _ = get_or_create_word(session, wtext)
            key = word.text.lower()
            if key in seen_norm:
                raise BespokePuzzleError(f'Duplicate word across puzzle: "{word.text}"')
            seen_norm.add(key)
            link_word_tag(session, word, tag)
            normalized_rows.append((gi, pi, tag, word))

    puzzle_id = str(uuid.uuid4())
    puzzle = Puzzle(id=puzzle_id)
    session.add(puzzle)
    session.flush()

    for gi, pi, tag, w in normalized_rows:
        session.add(
            PuzzleGroupItem(
                puzzle_id=puzzle_id,
                group_index=gi,
                position_in_group=pi,
                tag_id=tag.id,
                word_id=w.id,
            )
        )

    return puzzle_id


def load_bespoke_puzzle_response(session: Session, puzzle_id: str) -> PuzzleResponse | None:
    stmt = (
        select(Puzzle)
        .where(Puzzle.id == puzzle_id)
        .options(selectinload(Puzzle.group_items))
    )
    puzzle = session.scalar(stmt)
    if puzzle is None:
        return None

    items = sorted(
        puzzle.group_items,
        key=lambda r: (r.group_index, r.position_in_group),
    )
    if len(items) != 16:
        return None

    groups: list[_Group] = []
    for gi in range(4):
        rows = [r for r in items if r.group_index == gi]
        if len(rows) != 4:
            return None
        rows.sort(key=lambda r: r.position_in_group)
        tag = session.get(Tag, rows[0].tag_id)
        if tag is None or any(r.tag_id != tag.id for r in rows):
            return None
        words: list[Word] = []
        for r in rows:
            w = session.get(Word, r.word_id)
            if w is None:
                return None
            words.append(w)
        groups.append(_Group(tag=tag, words=words))

    flat: list[Word] = []
    for g in groups:
        flat.extend(g.words)
    random.shuffle(flat)

    solution = [
        PuzzleGroup(
            tag_id=g.tag.id,
            slug=g.tag.slug,
            label=g.tag.label,
            kind=g.tag.kind,
            word_ids=[w.id for w in g.words],
            words=[w.text for w in g.words],
        )
        for g in groups
    ]

    return PuzzleResponse(
        puzzle_id=puzzle.id,
        difficulty=0,
        words=[w.text for w in flat],
        word_ids=[w.id for w in flat],
        solution=solution,
    )
