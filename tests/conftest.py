"""Ensure admin token is set before app settings load (tests import app after conftest)."""

import os

os.environ.setdefault("JOINTED_ADMIN_TOKEN", "test-admin-token")
