from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import require_admin_token
from app.csv_import import import_words_tags_csv
from app.database import get_db
from app.schemas import ImportWordsCsvResponse

router = APIRouter(prefix="/v1", tags=["import"])

MAX_CSV_BYTES = 8 * 1024 * 1024


@router.post(
    "/import/words-csv",
    response_model=ImportWordsCsvResponse,
    dependencies=[Depends(require_admin_token)],
)
async def import_words_csv(
    file: UploadFile = File(..., description="UTF-8 CSV with headers word,tag"),
    db: Session = Depends(get_db),
) -> ImportWordsCsvResponse:
    """
    Bulk-merge word↔tag associations from a CSV file.

    **Format (header required):** long/tidy rows — one row per word–tag pair.

    - Required columns: `word` and `tag` (aliases: `text`/`lemma` for word; `category`/`label` for tag).
    - Optional: `tag_kind` (aliases `kind`, `type`) — used when creating a new tag.

    Example:

        word,tag
        bass,Fish
        bass,Instrument
        salmon,Fish
    """
    raw = await file.read()
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_CSV_BYTES // (1024 * 1024)} MB)",
        )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="File must be UTF-8") from e

    result = import_words_tags_csv(db, text)
    if result.row_errors:
        err0 = result.row_errors[0]
        if err0.startswith("CSV has no header") or err0.startswith("CSV must include"):
            db.rollback()
            raise HTTPException(status_code=400, detail=result.row_errors)

    db.commit()
    return ImportWordsCsvResponse(
        rows_read=result.rows_read,
        rows_skipped_empty=result.rows_skipped_empty,
        unique_words_created=result.unique_words_created,
        unique_tags_created=result.unique_tags_created,
        links_added=result.links_added,
        links_already_present=result.links_already_present,
        row_errors=result.row_errors,
    )
