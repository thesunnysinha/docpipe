"""Isolated application client for endpoint specifications."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client() -> TestClient:
    """Construct an application without reusing mutable state across cases."""
    return TestClient(create_app())
