import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_AUTH = {"Authorization": f"Bearer {os.environ.get('JOINTED_ADMIN_TOKEN', 'test-admin-token')}"}

_SAMPLE = {
    "categories": [
        {"label": "Test Alpha", "words": ["one", "two", "three", "four"]},
        {"label": "Test Beta", "words": ["five", "six", "seven", "eight"]},
        {"label": "Test Gamma", "words": ["nine", "ten", "eleven", "twelve"]},
        {"label": "Test Delta", "words": ["aa", "bb", "cc", "dd"]},
    ]
}


def test_create_and_fetch_bespoke_puzzle() -> None:
    r = client.post("/v1/puzzles", json=_SAMPLE, headers=_AUTH)
    assert r.status_code == 200, r.text
    pid = r.json()["puzzle_id"]
    assert len(pid) == 36

    g = client.get(f"/v1/puzzles/{pid}")
    assert g.status_code == 200
    body = g.json()
    assert body["puzzle_id"] == pid
    assert len(body["words"]) == 16
    assert len(body["solution"]) == 4


def test_bespoke_duplicate_word_400() -> None:
    bad = {
        "categories": [
            {"label": "A", "words": ["x", "y", "z", "q"]},
            {"label": "B", "words": ["x", "a", "b", "c"]},
            {"label": "C", "words": ["d", "e", "f", "g"]},
            {"label": "D", "words": ["h", "i", "j", "k"]},
        ]
    }
    r = client.post("/v1/puzzles", json=bad, headers=_AUTH)
    assert r.status_code == 400


def test_post_puzzles_requires_bearer() -> None:
    r = client.post("/v1/puzzles", json=_SAMPLE)
    assert r.status_code == 401
