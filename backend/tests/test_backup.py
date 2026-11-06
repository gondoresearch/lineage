import io
import json
import tarfile

import yaml

from backend.store import BACKUP_MANIFEST, app_version


def files_of(data: bytes) -> dict[str, bytes]:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        return {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}


def make_tar(entries: dict[str, bytes], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, body in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
        if symlink:
            info = tarfile.TarInfo(symlink)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
    return buf.getvalue()


def manifest(version: str | None = None) -> bytes:
    return json.dumps({"app": "lineage", "format": 1, "version": version or app_version(), "created": "2026-01-01T00:00:00+00:00"}).encode()


def restore(client, data: bytes, force: bool = False):
    return client.post("/api/restore", params={"force": force}, content=data, headers={"Content-Type": "application/gzip"})


def snapshot_of(example_dir) -> dict[str, str]:
    out = {"workspace.yaml": (example_dir / "workspace.yaml").read_text()}
    for f in sorted((example_dir / "descriptions").rglob("*.md")):
        out[f.relative_to(example_dir).as_posix()] = f.read_text()
    return out


# ------------------------------------------------------------------ version and backup


def test_version_endpoint(client):
    v = client.get("/api/version").json()["version"]
    assert v == app_version() and v[0].isdigit()  # from the installed package metadata (pyproject.toml)


def test_backup_contains_data_and_manifest(client, example_dir):
    client.patch("/api/groups/teaching", json={"name": "T2"})  # creates a .history snapshot
    r = client.get("/api/backup")
    assert r.status_code == 200 and r.headers["content-type"] == "application/gzip"
    cd = r.headers["content-disposition"]
    assert cd.startswith(f'attachment; filename="lineage-backup-{app_version()}-') and cd.endswith('.tar.gz"')
    files = files_of(r.content)
    m = json.loads(files.pop(BACKUP_MANIFEST))
    assert (m["app"], m["format"], m["version"]) == ("lineage", 1, app_version()) and m["created"]
    assert files.pop("workspace.yaml").decode() == (example_dir / "workspace.yaml").read_text()
    on_disk = {f.relative_to(example_dir).as_posix() for f in (example_dir / "descriptions").rglob("*.md")}
    assert set(files) == on_disk  # every description, nothing from .history
    assert not any(n.startswith(".history") for n in files)


# ------------------------------------------------------------------ restore


def test_restore_round_trip_and_undo(client, example_dir):
    backup = client.get("/api/backup").content
    before = snapshot_of(example_dir)
    # change things after the backup: rename, new description, delete a milestone with a description
    client.patch("/api/groups/teaching", json={"name": "Changed", "description": "new text"})
    client.delete("/api/milestones/spectral-filters.rejected")
    changed = snapshot_of(example_dir)
    assert changed != before
    r = restore(client, backup)
    assert r.status_code == 200
    assert r.json()["restored_version"] == app_version() and r.json()["current_version"] == app_version()
    assert snapshot_of(example_dir) == before  # files identical to the backed-up ones
    ws = client.get("/api/workspace").json()
    assert next(g for g in ws["groups"] if g["id"] == "teaching")["name"] == "Teaching"
    assert any(m["id"] == "spectral-filters.rejected" for m in ws["milestones"])
    # Undo reverts the restore
    assert client.post("/api/undo").status_code == 204
    assert snapshot_of(example_dir) == changed


def test_version_mismatch_needs_force(client, example_dir):
    files = files_of(client.get("/api/backup").content)
    files[BACKUP_MANIFEST] = manifest("0.0.9")
    data = make_tar(files)
    before = snapshot_of(example_dir)
    r = restore(client, data)
    assert r.status_code == 409
    body = r.json()
    assert (body["backup_version"], body["current_version"]) == ("0.0.9", app_version())
    assert "0.0.9" in body["errors"][0]
    assert snapshot_of(example_dir) == before  # nothing changed
    r = restore(client, data, force=True)
    assert r.status_code == 200 and r.json()["restored_version"] == "0.0.9"


def test_old_backup_with_closed_state_is_converted(client):
    files = files_of(client.get("/api/backup").content)
    raw = yaml.safe_load(files["workspace.yaml"])
    raw["kinds"] = [k for k in raw["kinds"] if k["id"] != "closed"]
    raw["states"].append({"id": "closed", "name": "closed", "line": "dotted", "waiting_on": "nobody"})
    for m in raw["milestones"]:
        if m["id"] == "bayesian-rainfall.v2":
            m["kind"], m["state"] = "draft", "closed"
    files["workspace.yaml"] = yaml.safe_dump(raw).encode()
    assert restore(client, make_tar(files)).status_code == 200
    ws = client.get("/api/workspace").json()
    assert next(m for m in ws["milestones"] if m["id"] == "bayesian-rainfall.v2")["kind"] == "closed"


def test_restore_works_when_current_data_is_broken(client, example_dir):
    backup = client.get("/api/backup").content
    (example_dir / "workspace.yaml").write_text("groups: [broken\n")
    assert client.get("/api/workspace").status_code == 500
    assert restore(client, backup).status_code == 200
    assert client.get("/api/workspace").status_code == 200


# ------------------------------------------------------------------ rejected archives leave data untouched


def rejected(client, example_dir, data: bytes, needle: str):
    before = snapshot_of(example_dir)
    r = restore(client, data, force=True)
    assert r.status_code == 422, r.json()
    assert any(needle in e for e in r.json()["errors"]), r.json()
    assert snapshot_of(example_dir) == before


def test_not_a_tar_gz(client, example_dir):
    rejected(client, example_dir, b"hello", "not a .tar.gz")


def test_missing_manifest(client, example_dir):
    rejected(client, example_dir, make_tar({"workspace.yaml": b"groups: []\n"}), "not a lineage backup")


def test_unsafe_paths(client, example_dir):
    rejected(client, example_dir, make_tar({BACKUP_MANIFEST: manifest(), "../evil.md": b"x"}), "Unsafe path")
    rejected(client, example_dir, make_tar({BACKUP_MANIFEST: manifest(), "/etc/evil": b"x"}), "Unsafe path")
    rejected(client, example_dir, make_tar({BACKUP_MANIFEST: manifest()}, symlink="descriptions/groups/x.md"), "regular files")


def test_unexpected_files(client, example_dir):
    rejected(client, example_dir, make_tar({BACKUP_MANIFEST: manifest(), "workspace.yaml": b"", "run.sh": b"x"}), "Unexpected file")


def test_invalid_workspace_in_backup(client, example_dir):
    bad = yaml.safe_dump({"groups": [{"id": "g", "name": "g", "color": "#000000"}],
                          "projects": [{"id": "p", "title": "p", "group": "nope"}]}).encode()
    rejected(client, example_dir, make_tar({BACKUP_MANIFEST: manifest(), "workspace.yaml": bad}), "not a valid workspace")


def test_backup_without_workspace(client, example_dir):
    rejected(client, example_dir, make_tar({BACKUP_MANIFEST: manifest()}), "no workspace.yaml")
