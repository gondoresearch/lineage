import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.accounts import Accounts
from backend.app import create_app
from backend.store import Store

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "papers"
PASSWORD = "correct horse"


@pytest.fixture(autouse=True)
def _no_demo(monkeypatch):
    """Tests create their own accounts; LINEAGE_DEMO is enabled explicitly where tested."""
    monkeypatch.setenv("LINEAGE_DEMO", "0")


@pytest.fixture
def root(tmp_path) -> Path:
    """The data folder: accounts.yaml and users/<name>/."""
    return tmp_path / "data"


@pytest.fixture
def example_dir(root) -> Path:
    """alice's workspace folder, a copy of the example data."""
    d = root / "users" / "alice"
    shutil.copytree(EXAMPLE, d)
    return d


@pytest.fixture
def example_ws(example_dir):
    """A fresh, valid copy of the example workspace (in memory)."""
    return Store(example_dir).read().model_copy(deep=True)


def make_client(root: Path) -> TestClient:
    return TestClient(create_app(root, frontend_dir=root / "no-frontend"), headers={"X-Lineage": "1"})


def login(c: TestClient, name: str, password: str = PASSWORD) -> TestClient:
    r = c.post("/api/login", json={"username": name, "password": password})
    assert r.status_code == 200, r.json()
    return c


@pytest.fixture
def client(root, example_dir) -> TestClient:
    """Logged in as alice, whose workspace is the example data."""
    Accounts(root).add("alice", PASSWORD)
    return login(make_client(root), "alice")


@pytest.fixture
def empty_client(tmp_path) -> TestClient:
    """Logged in as alice, a new user (so her workspace gets the starter vocabulary)."""
    root = tmp_path / "fresh"
    Accounts(root).add("alice", PASSWORD)
    return login(make_client(root), "alice")
