"""Text normalization for words and category labels (see docs/jointed_db_schema.md)."""

from __future__ import annotations

import re
import unicodedata

MAX_WORD_LEN = 128
MAX_CATEGORY_LABEL_LEN = 256


def normalize_text(s: str) -> str:
    """NFKC, trim, collapse internal whitespace, casefold."""
    t = unicodedata.normalize("NFKC", s)
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t.casefold()


def validate_word_input(raw: str) -> str:
    n = normalize_text(raw)
    if not n:
        raise ValueError("Empty word after normalization")
    if len(n) > MAX_WORD_LEN:
        raise ValueError(f"Word exceeds {MAX_WORD_LEN} characters after normalization")
    return n


def validate_category_label_input(raw: str) -> str:
    n = normalize_text(raw)
    if not n:
        raise ValueError("Empty category label after normalization")
    if len(n) > MAX_CATEGORY_LABEL_LEN:
        raise ValueError(
            f"Category label exceeds {MAX_CATEGORY_LABEL_LEN} characters after normalization"
        )
    return n
