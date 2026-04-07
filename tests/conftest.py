"""Test env + in-memory SQLite. App is imported only after tables exist."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("JOINTED_ADMIN_TOKEN", "test-admin-token")

import pytest
from fastapi.testclient import TestClient

from app.database import engine  # noqa: E402
from app.models import Base  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-admin-token"}
