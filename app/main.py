from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import puzzle

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Jointed", version="0.1.0")
app.include_router(puzzle.router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def puzzle_editor() -> FileResponse:
    """Simple HTML form to POST bespoke puzzles."""
    page = STATIC_DIR / "index.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="Editor page not found")
    return FileResponse(page)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
