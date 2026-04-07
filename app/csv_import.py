"""Import word↔tag rows from CSV (long format: one association per line)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.lexicon import LexiconError, get_or_create_tag, get_or_create_word, link_word_tag


@dataclass
class CsvImportResult:
    rows_read: int = 0
    rows_skipped_empty: int = 0
    """Distinct words that were newly inserted during this import."""
    unique_words_created: int = 0
    """Distinct tags that were newly inserted during this import."""
    unique_tags_created: int = 0
    links_added: int = 0
    links_already_present: int = 0
    row_errors: list[str] = field(default_factory=list)


# Headers we accept (first row). Values are canonical keys.
_WORD_ALIASES = frozenset({"word", "text", "lemma"})
_TAG_ALIASES = frozenset({"tag", "category", "label"})
_TAG_KIND_ALIASES = frozenset({"tag_kind", "kind", "type"})


def _norm_header(s: str) -> str:
    return s.strip().lower()


def _map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    """Map CSV column names to canonical keys: word, tag, tag_kind (optional)."""
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
    if "word" not in mapping or "tag" not in mapping:
        raise ValueError(
            "CSV must include columns for word and tag (e.g. word,tag). "
            f"Found: {fieldnames!r}"
        )
    return mapping


def import_words_tags_csv(session: Session, text: str) -> CsvImportResult:
    """
    Parse CSV text (UTF-8; BOM allowed). Each data row: one word and one tag to associate.

    - Words are unique by exact stored text (trimmed); new words are created as needed.
    - Tags are matched/created by label (same rules as bespoke puzzles).
    - Existing word–tag pairs are left unchanged (counts as link_already_present).
    """
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

        try:
            tag, tag_new = get_or_create_tag(session, t_raw, kind=kind)
            word, word_new = get_or_create_word(session, w_raw)
        except LexiconError as e:
            result.row_errors.append(f"Line {i}: {e}")
            continue

        if word_new:
            new_word_ids.add(word.id)
        if tag_new:
            new_tag_ids.add(tag.id)

        if link_word_tag(session, word, tag):
            result.links_added += 1
        else:
            result.links_already_present += 1

    result.unique_words_created = len(new_word_ids)
    result.unique_tags_created = len(new_tag_ids)
    return result
