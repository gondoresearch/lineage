import io
import shutil
import tarfile
import time

import pytest

from backend import accounts as A
from backend import manage
from backend.accounts import Accounts

from conftest import EXAMPLE, PASSWORD, login, make_client

PUBLIC = {"/api/login", "/api/version"}


def anonymous(root):
    return make_client(root)


def call(c, method, path):
    path = path.replace("{id}", "x")
    return c.request(method, path, json={} if method in ("post", "patch") else None)


# ------------------------------------------------------------------ login required


def test_every_api_route_needs_login(client, root):
    anon = anonymous(root)
    spec = client.get("/openapi.json").json()
    checked = 0
    for path, ops in spec["paths"].items():
        if path in PUBLIC or path == "/api/logout":
            continue
        for method in ops:
            r = call(anon, method, path)
            assert r.status_code == 401, (method, path, r.status_code)
            assert r.json() == {"errors": ["Not logged in."]}
            checked += 1
    assert checked > 20


def test_version_is_public(root, example_dir):
    Accounts(root).add("alice", PASSWORD)
    assert anonymous(root).get("/api/version").status_code == 200


def test_me(client):
    assert client.get("/api/me").json() == {"username": "alice", "admin": True, "must_change": False}  # first account: admin


def test_wrong_password_and_unknown_user(root, example_dir):
    Accounts(root).add("alice", PASSWORD)
    c = anonymous(root)
    for name, pw in (("alice", "nope"), ("nobody", PASSWORD), ("../etc", PASSWORD)):
        r = c.post("/api/login", json={"username": name, "password": pw})
        assert r.status_code == 401 and r.json() == {"errors": ["Wrong user name or password."]}
        assert A.COOKIE not in r.cookies
    assert c.get("/api/workspace").status_code == 401


def test_cookie_flags(root, example_dir):
    Accounts(root).add("alice", PASSWORD)
    r = anonymous(root).post("/api/login", json={"username": "alice", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "max-age=" in cookie


def test_lockout_after_failures(root, example_dir):
    Accounts(root).add("alice", PASSWORD)
    c = anonymous(root)
    for _ in range(A.Throttle.FREE):
        assert c.post("/api/login", json={"username": "alice", "password": "bad"}).status_code == 401
    r = c.post("/api/login", json={"username": "alice", "password": PASSWORD})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_throttle_doubles_and_resets():
    t = A.Throttle()
    k = ("alice", "1.2.3.4")
    for _ in range(t.FREE - 1):
        t.failed(k, now=0)
    assert t.wait(k, now=0) == 0
    t.failed(k, now=0)
    assert t.wait(k, now=0) == t.BASE
    t.failed(k, now=0)
    assert t.wait(k, now=0) == 2 * t.BASE
    t.succeeded(k)
    assert t.wait(k, now=0) == 0


def test_logout(client):
    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/workspace").status_code == 401


def test_tampered_and_expired_cookies(root, example_dir):
    acc = Accounts(root)
    acc.add("alice", PASSWORD)
    good = acc.make_session("alice")
    assert acc.session_user(good) == "alice"
    p64, sig = good.split(".")
    forged = A._b64(b"bob|1|" + str(int(time.time())).encode()) + "." + sig
    assert acc.session_user(forged) is None
    assert acc.session_user(p64 + "." + sig[:-2] + "AA") is None
    assert acc.session_user("garbage") is None and acc.session_user(None) is None
    old = acc.make_session("alice", now=time.time() - A.SESSION_SECONDS - 10)
    assert acc.session_user(old) is None
    c = anonymous(root)
    c.cookies.set(A.COOKIE, forged)
    assert c.get("/api/workspace").status_code == 401


def test_password_change_ends_other_sessions(root, example_dir):
    Accounts(root).add("alice", PASSWORD)
    a = login(make_client(root), "alice")
    b = login(make_client(root), "alice")
    r = a.post("/api/password", json={"current": PASSWORD, "new": "a new password"})
    assert r.status_code == 200
    assert a.get("/api/workspace").status_code == 200  # this session continues
    assert b.get("/api/workspace").status_code == 401  # the other one ended
    login(make_client(root), "alice", "a new password")


def test_password_change_checks(client):
    r = client.post("/api/password", json={"current": "wrong", "new": "a new password"})
    assert r.status_code == 422 and "current password" in r.json()["errors"][0]
    r = client.post("/api/password", json={"current": PASSWORD, "new": "short"})
    assert r.status_code == 422 and "at least 8" in r.json()["errors"][0]


def test_cli_passwd_and_deluser_end_sessions(client, root):
    Accounts(root).set_password("alice", "another password")
    assert client.get("/api/workspace").status_code == 401
    login(client, "alice", "another password")
    Accounts(root).remove("alice")
    assert client.get("/api/workspace").status_code == 401


# ------------------------------------------------------------------ csrf


def test_writes_need_the_header(client):
    for method, path in (("post", "/api/undo"), ("patch", "/api/groups/teaching"), ("delete", "/api/groups/teaching"),
                         ("post", "/api/restore"), ("post", "/api/logout")):
        r = client.request(method, path, headers={"X-Lineage": ""})
        assert r.status_code == 403, (method, path)
    assert client.get("/api/workspace", headers={"X-Lineage": ""}).status_code == 200


def test_login_needs_the_header(root, example_dir):
    Accounts(root).add("alice", PASSWORD)
    r = anonymous(root).post("/api/login", json={"username": "alice", "password": PASSWORD}, headers={"X-Lineage": ""})
    assert r.status_code == 403


# ------------------------------------------------------------------ isolation


def test_users_are_isolated(client, root):
    Accounts(root).add("bob", PASSWORD)
    bob = login(make_client(root), "bob")
    ws = bob.get("/api/workspace").json()
    assert ws["projects"] == [] and ws["groups"] == []
    assert bob.patch("/api/groups/teaching", json={"name": "x"}).status_code == 404
    assert bob.post("/api/groups", json={"name": "Bob's", "color": "#000000"}).status_code == 201
    assert "bob-s" not in {g["id"] for g in client.get("/api/workspace").json()["groups"]}
    with tarfile.open(fileobj=io.BytesIO(bob.get("/api/backup").content)) as tar:
        yaml_text = tar.extractfile("workspace.yaml").read().decode()
    assert "Bob's" in yaml_text and "spectral" not in yaml_text
    assert (root / "users" / "bob" / ".history").is_dir()
    assert not (root / "users" / "alice" / ".history").exists()  # bob's write did not touch alice
    assert bob.post("/api/undo").status_code == 204
    assert client.post("/api/undo").status_code == 409  # alice has nothing to undo


# ------------------------------------------------------------------ names and passwords


@pytest.mark.parametrize("name", ["../x", "A", "a/b", "", "-a", "a" * 33, "a b", "é"])
def test_invalid_names(root, name):
    with pytest.raises(A.AccountError):
        Accounts(root).add(name, PASSWORD)


def test_short_password_rejected(root):
    with pytest.raises(A.AccountError):
        Accounts(root).add("alice", "short")


def test_passwords_are_hashed(root):
    Accounts(root).add("alice", PASSWORD)
    text = (root / "accounts.yaml").read_text()
    assert PASSWORD not in text and "scrypt$" in text
    assert A.verify_password(PASSWORD, Accounts(root).get("alice")["password"])
    assert not A.verify_password("x", "not-a-hash")


def test_hand_edit_of_accounts_is_picked_up(client, root):
    (root / "accounts.yaml").write_text("users: {}\n")
    assert client.get("/api/workspace").status_code == 401


def test_broken_accounts_file_fails_closed(client, root):
    (root / "accounts.yaml").write_text("users: [broken\n")
    assert client.get("/api/workspace").status_code == 401


# ------------------------------------------------------------------ demo account


def test_showcase_accounts_on_first_start(tmp_path, monkeypatch):
    monkeypatch.setenv("LINEAGE_DEMO", "1")
    monkeypatch.setenv("LINEAGE_EXAMPLES", str(EXAMPLE.parent))
    root = tmp_path / "data"
    c = login(make_client(root), "demo", "demo")
    ws = c.get("/api/workspace").json()
    assert "spectral-filters" in {p["id"] for p in ws["projects"]}
    lin = login(make_client(root), "lineage", "lineage").get("/api/workspace").json()
    assert "main" in {p["id"] for p in lin["projects"]}
    assert {k["id"] for k in lin["kinds"]} == {"commit", "pull-request", "release", "issue", "closed"}
    assert Accounts(root).admins() == ["admin"]  # the default admin; showcase accounts never are
    assert Accounts(root).add("alice", PASSWORD) is False


def test_demo_disabled(tmp_path):
    root = tmp_path / "data"
    make_client(root)
    assert Accounts(root).names() == ["admin"]  # no showcase accounts, but the default admin
    assert not (root / "users" / "demo").exists() and not (root / "users" / "lineage").exists()


def test_demo_not_recreated(root, example_dir, monkeypatch):
    monkeypatch.setenv("LINEAGE_DEMO", "1")
    Accounts(root).add("alice", PASSWORD)
    make_client(root)
    assert Accounts(root).names() == ["alice"]


# ------------------------------------------------------------------ CLI


def run(root, *args, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin + "\n"))
    return manage.main(["--data-dir", str(root), *args])


def test_cli_adduser_list_deluser(root, monkeypatch, capsys):
    assert run(root, "adduser", "carol", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 0
    assert run(root, "adduser", "carol", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 1
    assert run(root, "adduser", "dave", "--password-stdin", stdin="short", monkeypatch=monkeypatch) == 1
    capsys.readouterr()
    assert run(root, "list") == 0 and capsys.readouterr().out.splitlines() == ["carol  (admin)"]  # first account
    login(make_client(root), "carol").get("/api/workspace")  # creates her workspace
    assert (root / "users" / "carol" / "workspace.yaml").exists()
    assert run(root, "deluser", "carol") == 0 and (root / "users" / "carol").exists()
    assert run(root, "adduser", "carol", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 0
    assert run(root, "deluser", "carol", "--purge") == 0 and not (root / "users" / "carol").exists()
    assert run(root, "deluser", "carol") == 1


def test_cli_adopt(root, monkeypatch):
    root.mkdir()
    shutil.copy(EXAMPLE / "workspace.yaml", root / "workspace.yaml")
    shutil.copytree(EXAMPLE / "descriptions", root / "descriptions")
    (root / ".history").mkdir()
    assert run(root, "adduser", "erin", "--adopt", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 0
    assert not (root / "workspace.yaml").exists() and not (root / "descriptions").exists()
    d = root / "users" / "erin"
    assert (d / "workspace.yaml").exists() and (d / "descriptions").is_dir() and (d / ".history").is_dir()
    ws = login(make_client(root), "erin").get("/api/workspace").json()
    assert "spectral-filters" in {p["id"] for p in ws["projects"]}
    # nothing left to adopt
    assert run(root, "adduser", "frank", "--adopt", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 1


def test_cli_from(root, monkeypatch):
    assert run(root, "adduser", "gina", "--from", str(EXAMPLE), "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch) == 0
    ws = login(make_client(root), "gina").get("/api/workspace").json()
    assert "spectral-filters" in {p["id"] for p in ws["projects"]}


def test_cli_passwd(root, monkeypatch):
    run(root, "adduser", "hal", "--password-stdin", stdin=PASSWORD, monkeypatch=monkeypatch)
    assert run(root, "passwd", "hal", "--password-stdin", stdin="new password!", monkeypatch=monkeypatch) == 0
    login(make_client(root), "hal", "new password!")
    assert run(root, "passwd", "nobody", "--password-stdin", stdin="new password!", monkeypatch=monkeypatch) == 1
