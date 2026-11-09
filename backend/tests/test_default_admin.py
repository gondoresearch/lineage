from backend import accounts as A
from backend.accounts import Accounts

from conftest import PASSWORD, login, make_client


def test_fresh_install_gets_admin_admin_that_must_change(tmp_path):
    root = tmp_path / "data"
    c = login(make_client(root), "admin", "admin")
    assert Accounts(root).admins() == ["admin"]
    assert c.get("/api/me").json() == {"username": "admin", "admin": True, "must_change": True}
    # nothing else works until the password is changed
    for method, path in (("get", "/api/workspace"), ("get", "/api/admin/users"), ("post", "/api/undo"),
                         ("get", "/api/backup")):
        r = c.request(method, path)
        assert r.status_code == 403 and r.json()["must_change"] is True, (method, path)
    assert c.post("/api/password", json={"current": "admin", "new": "short"}).status_code == 422
    r = c.post("/api/password", json={"current": "admin", "new": "a real password"})
    assert r.status_code == 200 and r.json()["must_change"] is False
    assert c.get("/api/workspace").status_code == 200
    assert c.get("/api/admin/users").status_code == 200
    assert "must_change" not in Accounts(root).get("admin")


def test_cli_passwd_clears_must_change(tmp_path):
    root = tmp_path / "data"
    make_client(root)
    Accounts(root).set_password("admin", "another password")
    assert not Accounts(root).must_change("admin")
    login(make_client(root), "admin", "another password").get("/api/workspace").raise_for_status()


def test_existing_install_without_admin_gets_one(root, example_dir):
    Accounts(root).add("alice", PASSWORD, admin=False)
    make_client(root)
    assert Accounts(root).admins() == ["admin"]
    assert Accounts(root).must_change("admin")


def test_no_default_admin_when_there_is_an_admin(client, root):
    assert Accounts(root).names() == ["alice"]  # alice is admin: no 'admin' account added
    make_client(root)
    assert Accounts(root).names() == ["alice"]


def test_name_taken_by_a_plain_user(root, example_dir):
    Accounts(root).add("admin", PASSWORD, admin=False)
    make_client(root)
    assert Accounts(root).admins() == []  # not promoted silently; the log says how to make one
    assert not Accounts(root).must_change("admin")


def test_deleting_the_last_admin_brings_admin_back_on_next_start(tmp_path):
    root = tmp_path / "data"
    make_client(root)
    Accounts(root).set_password("admin", "a real password")
    Accounts(root).remove("admin")
    make_client(root)
    assert Accounts(root).must_change("admin")
    assert A.verify_password("admin", Accounts(root).get("admin")["password"])
