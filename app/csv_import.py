"""Import word↔category rows from CSV (long format: one association per line)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.lexicon import CANONICAL_CONNECTION_TYPES, LexiconError, get_or_create_category, get_or_create_word, link_word_category


@dataclass
class CsvImportResult:
    rows_read: int = 0
    rows_skipped_empty: int = 0
    unique_words_created: int = 0
    unique_tags_created: int = 0
    links_added: int = 0
    links_already_present: int = 0
    row_errors: list[str] = field(default_factory=list)


_WORD_ALIASES = frozenset({"word", "text", "lemma"})
_TAG_ALIASES = frozenset({"tag", "category", "label"})
_TAG_KIND_ALIASES = frozenset({"tag_kind", "kind", "type"})
_DIFFICULTY_ALIASES = frozenset({"difficulty", "diff"})
_ABSTRACTION_ALIASES = frozenset({"abstraction_level", "abstraction"})
_CONNECTION_ALIASES = frozenset({"connection_type", "connection"})
_NOTES_ALIASES = frozenset({"notes", "note"})
_DISPLAY_LABEL_ALIASES = frozenset({"display_label", "category_display", "puzzle_display"})


def _norm_header(s: str) -> str:
    return s.strip().lower()


def _map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise ValueError("CSV has no header row")
    mapping: dict[str, str] = {}
    for raw in fieldnames:
        key = _norm_header(raw)
        if key in _WORD_ALIASES:
            mapping["word"] = raw
        elif key in _TAG_ALIASES:
            mapping["tag"] = raw
        elif key in _TAG_KIND_ALIASES:
            mapping["tag_kind"] = raw
        elif key in _DIFFICULTY_ALIASES:
            mapping["difficulty"] = raw
        elif key in _ABSTRACTION_ALIASES:
            mapping["abstraction_level"] = raw
        elif key in _CONNECTION_ALIASES:
            mapping["connection_type"] = raw
        elif key in _NOTES_ALIASES:
            mapping["notes"] = raw
        elif key in _DISPLAY_LABEL_ALIASES:
            mapping["display_label"] = raw
    if "word" not in mapping or "tag" not in mapping:
        raise ValueError(
            "CSV must include columns for word and tag (e.g. word,tag). "
            f"Found: {fieldnames!r}"
        )
    return mapping


def _opt_int(s: str) -> int | None:
    t = s.strip()
    if not t:
        return None
    return int(t)


def import_words_tags_csv(session: Session, text: str) -> CsvImportResult:
    result = CsvImportResult()
    new_word_ids: set[int] = set()
    new_tag_ids: set[int] = set()
    stream = io.StringIO(text.lstrip("\ufeff"))
    reader = csv.DictReader(stream)
    try:
        col = _map_headers(reader.fieldnames)
    except ValueError as e:
        result.row_errors.append(str(e))
        return result

    word_col, tag_col = col["word"], col["tag"]
    kind_col = col.get("tag_kind")
    diff_col = col.get("difficulty")
    abs_col = col.get("abstraction_level")
    conn_col = col.get("connection_type")
    notes_col = col.get("notes")
    disp_col = col.get("display_label")

    for i, row in enumerate(reader, start=2):
        result.rows_read += 1
        w_raw = (row.get(word_col) or "").strip()
        t_raw = (row.get(tag_col) or "").strip()
        if not w_raw and not t_raw:
            result.rows_skipped_empty += 1
            continue
        if not w_raw or not t_raw:
            result.row_errors.append(
                f"Line {i}: both word and tag are required (got word={w_raw!r} tag={t_raw!r})"
            )
            continue
        kind = "semantic"
        if kind_col:
            k = (row.get(kind_col) or "").strip()
            if k:
                kind = k[:64]

        difficulty: int | None = None
        abstraction_level: int | None = None
        if diff_col:
            try:
                difficulty = _opt_int(row.get(diff_col) or "")
            except ValueError:
                result.row_errors.append(f"Line {i}: invalid difficulty")
                continue
        if abs_col:
            try:
                abstraction_level = _opt_int(row.get(abs_col) or "")
            except ValueError:
                result.row_errors.append(f"Line {i}: invalid abstraction_level")
                continue

        connection_type: str | None = None
        if conn_col:
            connection_type = (row.get(conn_col) or "").strip() or None
            if connection_type and connection_type not in CANONICAL_CONNECTION_TYPES:
                result.row_errors.append(
                    f"Line {i}: connection_type must be one of {sorted(CANONICAL_CONNECTION_TYPES)}"
                )
                continue

        notes: str | None = None
        if notes_col:
            n = (row.get(notes_col) or "").strip()
            notes = n or None

        metadata_extra: dict | None = None
        if disp_col:
            d = (row.get(disp_col) or "").strip()
            if d:
                metadata_extra = {"display_label": d}

        try:
            category, category_new = get_or_create_category(session, t_raw, kind=kind)
            word, word_new = get_or_create_word(session, w_raw)
        except LexiconError as e:
            result.row_errors.append(f"Line {i}: {e}")
            continue

        if word_new:
            new_word_ids.add(word.word_id)
        if category_new:
            new_tag_ids.add(category.category_id)

        try:
            created = link_word_category(
                session,
                word,
                category,
                difficulty=difficulty,
                abstraction_level=abstraction_level,
                connection_type=connection_type,
                notes=notes,
                metadata_extra=metadata_extra,
            )
        except LexiconError as e:
            result.row_errors.append(f"Line {i}: {e}")
            continue

        if created:
            result.links_added += 1
        else:
            result.links_already_present += 1

    result.unique_words_created = len(new_word_ids)
    result.unique_tags_created = len(new_tag_ids)
    return result
