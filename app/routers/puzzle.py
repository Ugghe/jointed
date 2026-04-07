from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.puzzle_generator import PuzzleGenerationError, generate_disjoint_puzzle
from app.schemas import PuzzleGroup, PuzzleResponse

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
