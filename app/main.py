from fastapi import FastAPI

from app.routers import puzzle

app = FastAPI(title="Jointed", version="0.1.0")
app.include_router(puzzle.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
