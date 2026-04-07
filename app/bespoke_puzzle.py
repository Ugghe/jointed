from __future__ import annotations

import random
import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.lexicon import get_or_create_category, get_or_create_word, link_word_category, slugify_label
from app.models import Category, Puzzle, PuzzleCategory, PuzzleWord, Word
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
    resolved: list[tuple[Category, str, list[Word]]] = []

    for gi, cat in enumerate(categories):
        if len(cat.words) != 4:
            raise BespokePuzzleError(f"Category {gi + 1} must have exactly 4 words")
        display = cat.label.strip()
        category, _ = get_or_create_category(session, cat.label)
        wlist: list[Word] = []
        for wtext in cat.words:
            word, _ = get_or_create_word(session, wtext)
            key = word.word
            if key in seen_norm:
                raise BespokePuzzleError(f'Duplicate word across puzzle: "{word.word}"')
            seen_norm.add(key)
            link_word_category(session, word, category)
            wlist.append(word)
        resolved.append((category, display, wlist))

    puzzle_id = uuid.uuid4()
    session.add(Puzzle(puzzle_id=puzzle_id, status="draft"))
    session.flush()

    for gi, (category, display, _wlist) in enumerate(resolved):
        session.add(
            PuzzleCategory(
                puzzle_id=puzzle_id,
                category_id=category.category_id,
                display_label=display,
                sort_order=gi + 1,
            )
        )
    session.flush()

    for category, _display, wlist in resolved:
        for word in wlist:
            session.add(
                PuzzleWord(
                    puzzle_id=puzzle_id,
                    word_id=word.word_id,
                    category_id=category.category_id,
                )
            )

    return str(puzzle_id)


def _category_kind(category: Category) -> str:
    if category.metadata_ and isinstance(category.metadata_, dict):
        k = category.metadata_.get("kind")
        if isinstance(k, str) and k:
            return k
    return "semantic"


def load_bespoke_puzzle_response(session: Session, puzzle_id: str) -> PuzzleResponse | None:
    try:
        pid = uuid.UUID(puzzle_id)
    except ValueError:
        return None

    stmt = (
        select(Puzzle)
        .where(Puzzle.puzzle_id == pid)
        .options(
            selectinload(Puzzle.puzzle_categories).selectinload(PuzzleCategory.category),
        )
    )
    puzzle = session.scalar(stmt)
    if puzzle is None:
        return None

    pcs = sorted(puzzle.puzzle_categories, key=lambda pc: pc.sort_order or 0)
    if len(pcs) != 4:
        return None

    pw_rows = list(session.scalars(select(PuzzleWord).where(PuzzleWord.puzzle_id == pid)).all())
    if len(pw_rows) != 16:
        return None

    groups: list[_Group] = []
    for pc in pcs:
        cat = pc.category
        if cat is None:
            return None
        wrows = [r for r in pw_rows if r.category_id == cat.category_id]
        if len(wrows) != 4:
            return None
        words: list[Word] = []
        for r in sorted(wrows, key=lambda x: x.word_id):
            w = session.get(Word, r.word_id)
            if w is None:
                return None
            words.append(w)
        groups.append(_Group(category=cat, words=words))

    flat: list[Word] = []
    for g in groups:
        flat.extend(g.words)
    random.shuffle(flat)

    solution = []
    for g in groups:
        disp = None
        for pc in pcs:
            if pc.category_id == g.category.category_id:
                disp = pc.display_label
                break
        label_out = disp if disp else g.category.label
        solution.append(
            PuzzleGroup(
                tag_id=g.category.category_id,
                slug=slugify_label(label_out),
                label=label_out,
                kind=_category_kind(g.category),
                word_ids=[w.word_id for w in g.words],
                words=[w.word for w in g.words],
            )
        )

    return PuzzleResponse(
        puzzle_id=str(puzzle.puzzle_id),
        difficulty=0,
        words=[w.word for w in flat],
        word_ids=[w.word_id for w in flat],
        solution=solution,
    )
