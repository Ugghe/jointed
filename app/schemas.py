from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class PuzzleGroup(BaseModel):
    tag_id: int
    slug: str
    label: str
    kind: str
    word_ids: list[int]
    words: list[str]


class PuzzleResponse(BaseModel):
    puzzle_id: str
    difficulty: int = Field(description="0 = strict disjoint groups; higher = more overlap (future)")
    words: list[str] = Field(description="All 16 words, shuffled for the board")
    word_ids: list[int] = Field(description="Parallel ids for the same shuffle order")
    solution: list[PuzzleGroup]


class ErrorResponse(BaseModel):
    detail: str


class BespokeCategoryIn(BaseModel):
    label: str
    words: list[str]


class BespokePuzzleCreate(BaseModel):
    """Exactly four categories, each with four words."""

    categories: list[BespokeCategoryIn]

    @field_validator("categories")
    @classmethod
    def four_categories(cls, v: list[BespokeCategoryIn]) -> list[BespokeCategoryIn]:
        if len(v) != 4:
            raise ValueError("Must provide exactly 4 categories")
        return v

    @model_validator(mode="after")
    def words_nonempty(self) -> BespokePuzzleCreate:
        for i, c in enumerate(self.categories):
            if not c.label.strip():
                raise ValueError(f"Category {i + 1}: label must be non-empty")
            if len(c.words) != 4:
                raise ValueError(f"Category {i + 1} must have exactly 4 words")
            for j, w in enumerate(c.words):
                if not isinstance(w, str) or not w.strip():
                    raise ValueError(f"Category {i + 1}, word {j + 1}: must be non-empty")
        return self


class CreateBespokePuzzleResponse(BaseModel):
    puzzle_id: str


class ImportWordsCsvResponse(BaseModel):
    rows_read: int
    rows_skipped_empty: int
    unique_words_created: int
    unique_tags_created: int
    links_added: int
    links_already_present: int
    row_errors: list[str]
