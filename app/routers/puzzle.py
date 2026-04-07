from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.bespoke_puzzle import BespokePuzzleError, load_bespoke_puzzle_response, save_bespoke_puzzle
from app.bespoke_puzzle import CategoryInput as SaveCategoryInput
from app.database import get_db
from app.puzzle_generator import PuzzleGenerationError, generate_disjoint_puzzle
from app.schemas import (
    BespokePuzzleCreate,
    CreateBespokePuzzleResponse,
    PuzzleGroup,
    PuzzleResponse,
)

router = APIRouter(prefix="/v1", tags=["puzzle"])


@router.get("/puzzle", response_model=PuzzleResponse)
def get_puzzle(difficulty: int = 0, db: Session = Depends(get_db)) -> PuzzleResponse:
    """
    Dev mode: returns shuffled board words plus full solution (tags + word groupings).
    """
    try:
        puzzle_id, words, word_ids, groups = generate_disjoint_puzzle(
            db, difficulty=difficulty
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PuzzleGenerationError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

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
        puzzle_id=puzzle_id,
        difficulty=difficulty,
        words=words,
        word_ids=word_ids,
        solution=solution,
    )


@router.post("/puzzles", response_model=CreateBespokePuzzleResponse)
def create_bespoke_puzzle(
    body: BespokePuzzleCreate,
    db: Session = Depends(get_db),
) -> CreateBespokePuzzleResponse:
    """
    Save a hand-built puzzle: upserts words/tags, stores rows for later fetch by id.
    """
    cats = [
        SaveCategoryInput(label=c.label, words=c.words) for c in body.categories
    ]
    try:
        puzzle_id = save_bespoke_puzzle(db, cats)
        db.commit()
    except BespokePuzzleError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CreateBespokePuzzleResponse(puzzle_id=puzzle_id)


@router.get("/puzzles/{puzzle_id}", response_model=PuzzleResponse)
def get_bespoke_puzzle_by_id(
    puzzle_id: UUID,
    db: Session = Depends(get_db),
) -> PuzzleResponse:
    """Load a puzzle previously saved via POST /v1/puzzles."""
    result = load_bespoke_puzzle_response(db, str(puzzle_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return result
