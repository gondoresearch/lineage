import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.store import Store

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "papers"


@pytest.fixture
def example_dir(tmp_path) -> Path:
    d = tmp_path / "data"
    shutil.copytree(EXAMPLE, d)
    return d


@pytest.fixture
def example_ws(example_dir):
    """A fresh, valid copy of the example workspace (in memory)."""
    return Store(example_dir).read().model_copy(deep=True)


@pytest.fixture
def client(example_dir) -> TestClient:
    return TestClient(create_app(example_dir, frontend_dir=example_dir / "no-frontend"))


@pytest.fixture
def empty_client(tmp_path) -> TestClient:
    d = tmp_path / "fresh"
    return TestClient(create_app(d, frontend_dir=d / "no-frontend"))
