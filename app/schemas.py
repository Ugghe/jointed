from pydantic import BaseModel, Field


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
