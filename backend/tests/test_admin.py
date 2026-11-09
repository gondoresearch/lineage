import io
import tarfile

import pytest

from backend import accounts as A
from backend import manage
from backend.accounts import Accounts

from conftest import PASSWORD, login, make_client


@pytest.fixture
def setup(client, root):
    """alice (admin, first account, example data), bob (plain user, with one group of his own)."""
    Accounts(root).add("bob", PASSWORD)
    bob = login(make_client(root), "bob")
    assert bob.post("/api/groups", json={"name": "Bob's", "color": "#000000"}).status_code == 201
    return client, bob


def names(c):
    return [u["username"] for u in c.get("/api/admin/users").json()]


# ------------------------------------------------------------------ who is admin


def test_first_account_is_admin_demo_never(root, tmp_path, monkeypatch):
    acc = Accounts(root)
    assert acc.add(A.DEMO_NAME, "demo", enforce_length=False) is False
    assert acc.add("alice", PASSWORD) is True
    assert acc.add("bob", PASSWORD) is False
    assert acc.admins() == ["alice"]
    assert "admin" not in acc.get("bob")  # plain users have no flag in the file


def test_new_admin_when_none_left(root):
    acc = Accounts(root)
    acc.add("alice", PASSWORD)
    acc.set_admin("alice", False)
    assert acc.add("carol", PASSWORD) is True


def test_me_reports_admin(setup):
    alice, bob = setup
    assert alice.get("/api/me").json()["admin"] is True
    assert bob.get("/api/me").json()["admin"] is False


def test_admin_routes_need_admin(setup, root):
    _, bob = setup
    for method, path in (("get", "/api/admin/users"), ("post", "/api/admin/users"),
                         ("post", "/api/admin/users/alice/password"), ("delete", "/api/admin/users/alice"),
                         ("get", "/api/admin/users/alice/backup"), ("post", "/api/admin/users/alice/restore")):
        assert bob.request(method, path, json={}).status_code == 403, (method, path)
        assert make_client(root).request(method, path, json={}).status_code == 401, (method, path)


def test_demotion_takes_effect_immediately(setup, root):
    alice, _ = setup
    Accounts(root).set_admin("alice", False)
    assert alice.get("/api/admin/users").status_code == 403


# ------------------------------------------------------------------ managing users


def test_list_users_without_hashes(setup):
    alice, _ = setup
    users = alice.get("/api/admin/users").json()
    assert [(u["username"], u["admin"]) for u in users] == [("alice", True), ("bob", False)]
    assert all(set(u) == {"username", "admin", "created", "must_change"} for u in users)


def test_create_user(setup, root):
    alice, _ = setup
    r = alice.post("/api/admin/users", json={"username": "carol", "password": PASSWORD})
    assert r.status_code == 201 and r.json()["admin"] is False
    login(make_client(root), "carol")
    assert alice.post("/api/admin/users", json={"username": "carol", "password": PASSWORD}).status_code == 409
    assert alice.post("/api/admin/users", json={"username": "../x", "password": PASSWORD}).status_code == 422
    assert alice.post("/api/admin/users", json={"username": "dave", "password": "short"}).status_code == 422


def test_set_password(setup, root):
    alice, bob = setup
    assert alice.post("/api/admin/users/bob/password", json={"password": "bob's new one"}).status_code == 204
    assert bob.get("/api/workspace").status_code == 401  # logged out everywhere
    login(make_client(root), "bob", "bob's new one")
    assert alice.post("/api/admin/users/bob/password", json={"password": "short"}).status_code == 422


def test_delete_keeps_or_purges_workspace(setup, root):
    alice, bob = setup
    assert alice.delete("/api/admin/users/bob").status_code == 204
    assert bob.get("/api/workspace").status_code == 401
    assert (root / "users" / "bob" / "workspace.yaml").exists()
    # re-created with the same name: the workspace comes back
    alice.post("/api/admin/users", json={"username": "bob", "password": PASSWORD})
    ws = login(make_client(root), "bob").get("/api/workspace").json()
    assert "Bob's" in {g["name"] for g in ws["groups"]}
    assert alice.delete("/api/admin/users/bob?purge=true").status_code == 204
    assert not (root / "users" / "bob").exists()
    # and once more: a fresh workspace
    alice.post("/api/admin/users", json={"username": "bob", "password": PASSWORD})
    assert login(make_client(root), "bob").get("/api/workspace").json()["groups"] == []


def test_unknown_user_is_404(setup):
    alice, _ = setup
    assert alice.delete("/api/admin/users/nobody").status_code == 404
    assert alice.get("/api/admin/users/nobody/backup").status_code == 404
    assert alice.post("/api/admin/users/nobody/password", json={"password": PASSWORD + "x"}).status_code == 404


def test_admins_are_not_managed_from_the_web(setup, root):
    alice, _ = setup
    Accounts(root).add("root2", PASSWORD, admin=True)
    for method, path, body in (("delete", "/api/admin/users/alice", None), ("delete", "/api/admin/users/root2", None),
                               ("post", "/api/admin/users/root2/password", {"password": "takeover!!"}),
                               ("get", "/api/admin/users/root2/backup", None),
                               ("post", "/api/admin/users/root2/restore", None)):
        r = alice.request(method, path, json=body)
        assert r.status_code == 409 and "command line" in r.json()["errors"][0], (method, path)
    assert names(alice) == ["alice", "bob", "root2"]


# ------------------------------------------------------------------ backups of other users


def test_backup_and_restore_another_user(setup):
    alice, bob = setup
    r = alice.get("/api/admin/users/bob/backup")
    assert r.status_code == 200 and 'filename="lineage-backup-bob-' in r.headers["content-disposition"]
    with tarfile.open(fileobj=io.BytesIO(r.content)) as tar:
        text = tar.extractfile("workspace.yaml").read().decode()
    assert "Bob's" in text and "spectral" not in text
    archive = r.content

    bob.patch("/api/groups/bob-s", json={"name": "Renamed"})
    r = alice.post("/api/admin/users/bob/restore", content=archive, headers={"Content-Type": "application/gzip"})
    assert r.status_code == 200
    assert "Bob's" in {g["name"] for g in bob.get("/api/workspace").json()["groups"]}
    assert bob.post("/api/undo").status_code == 204  # bob can undo the admin's restore
    assert "Renamed" in {g["name"] for g in bob.get("/api/workspace").json()["groups"]}
    # alice's own workspace is untouched
    assert "spectral-filters" in {p["id"] for p in alice.get("/api/workspace").json()["projects"]}


def test_restore_rejects_bad_archives(setup):
    alice, _ = setup
    r = alice.post("/api/admin/users/bob/restore", content=b"nope", headers={"Content-Type": "application/gzip"})
    assert r.status_code == 422


# ------------------------------------------------------------------ CLI


def run(root, *args, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin + "\n"))
    return manage.main(["--data-dir", str(root), *args])


def test_cli_admin_flag_and_list(root, monkeypatch, capsys):
    assert run(root, "adduser", "alice", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 0
    assert "Created admin 'alice'" in capsys.readouterr().out
    run(root, "adduser", "bob", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch)
    run(root, "adduser", "carol", "--admin", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch)
    capsys.readouterr()
    run(root, "list")
    assert capsys.readouterr().out.splitlines() == ["alice  (admin)", "bob", "carol  (admin)"]
    assert run(root, "admin", "bob", "on") == 0 and Accounts(root).is_admin("bob")
    assert run(root, "admin", "bob", "off") == 0 and not Accounts(root).is_admin("bob")
    assert run(root, "admin", "nobody", "on") == 1


def test_cli_warns_when_no_admin_left(root, monkeypatch, capsys):
    run(root, "adduser", "alice", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch)
    run(root, "admin", "alice", "off")
    assert "no admin account left" in capsys.readouterr().err


def test_cli_demo_cannot_be_admin_with_demo_password(root, monkeypatch):
    Accounts(root).add(A.DEMO_NAME, "demo", enforce_length=False)
    assert run(root, "admin", "demo", "on") == 1
    Accounts(root).add("lineage", "lineage", enforce_length=False)
    assert run(root, "admin", "lineage", "on") == 1
    run(root, "passwd", "demo", "--password-stdin", stdin="a real password", monkeypatch=monkeypatch)
    assert run(root, "admin", "demo", "on") == 0
