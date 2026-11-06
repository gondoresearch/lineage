"""Loading and saving the data folder: atomic writes, snapshots, undo,
reloading after hand edits, and backup / restore archives."""

import importlib.metadata
import io
import json
import os
import shutil
import tarfile
import threading
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import yaml
from pydantic import ValidationError

from . import graph, seed
from . import models as M

KEEP_SNAPSHOTS = 20
BACKUP_MANIFEST = "lineage-backup.json"
BACKUP_FORMAT = 1
MAX_BACKUP_BYTES = 50 * 1024 * 1024  # compressed upload
MAX_BACKUP_CONTENT = 200 * 1024 * 1024  # uncompressed total


def app_version() -> str:
    """The running lineage version (from the installed package metadata)."""
    try:
        return importlib.metadata.version("lineage")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+unknown"
TMP_PREFIX = ".tmp-"
_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
_Dumper = getattr(yaml, "CSafeDumper", yaml.SafeDumper)


class Broken(Exception):
    """The files on disk do not form a valid workspace (HTTP 500)."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class NothingToUndo(Exception):
    pass


class BadBackup(Exception):
    """The uploaded file is not a usable lineage backup (HTTP 422)."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class VersionMismatch(Exception):
    """The backup was made by another lineage version (HTTP 409 unless forced)."""

    def __init__(self, backup: str, current: str):
        super().__init__(f"backup {backup}, running {current}")
        self.backup = backup
        self.current = current


def parse_workspace(yaml_text: str, descriptions: dict[tuple[str, str], str]) -> tuple[M.Workspace | None, list[str]]:
    """Build and validate a workspace from workspace.yaml text and description
    texts keyed by (type, id). Returns (workspace, []) or (None, errors)."""
    try:
        raw = yaml.load(yaml_text, Loader=_Loader)
    except yaml.YAMLError as e:
        return None, [f"workspace.yaml: {e}"]
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return None, ["workspace.yaml: the top level must be a mapping."]
    raw = graph.migrate(raw)
    try:
        ws = M.Workspace.model_validate(raw)
    except ValidationError as e:
        return None, [f"workspace.yaml: {m}" for m in graph.pydantic_messages(e)]
    for t in graph.TYPES:
        entities = graph.by_id(ws, t)
        for (dt, eid), text in descriptions.items():
            if dt == t and eid in entities:
                entities[eid].description = text
    errs = graph.validate(ws)
    return (None, errs) if errs else (ws, [])


def read_backup(data: bytes) -> tuple[dict, str, dict[tuple[str, str], str]]:
    """Check a backup archive and return (manifest, workspace.yaml text, descriptions).
    Only regular files at the expected paths are accepted."""
    if len(data) > MAX_BACKUP_BYTES:
        raise BadBackup([f"The file is larger than {MAX_BACKUP_BYTES // (1024 * 1024)} MB."])
    try:
        tar = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
        members = tar.getmembers()
    except (tarfile.TarError, EOFError, zlib.error, OSError):
        raise BadBackup(["This is not a .tar.gz file."]) from None
    files: dict[str, bytes] = {}
    total = 0
    with tar:
        for m in members:
            path = PurePosixPath(m.name)
            if path.is_absolute() or ".." in path.parts:
                raise BadBackup([f"Unsafe path in the archive: {m.name}"])
            if m.isdir():
                continue
            if not m.isfile():
                raise BadBackup([f"Only regular files are allowed in a backup: {m.name}"])
            name = path.as_posix().removeprefix("./")
            parts = name.split("/")
            allowed = name in (BACKUP_MANIFEST, "workspace.yaml") or (
                len(parts) == 3 and parts[0] == "descriptions" and parts[1] in graph.TYPES and parts[2].endswith(".md")
            )
            if not allowed:
                raise BadBackup([f"Unexpected file in the archive: {m.name}"])
            total += m.size
            if total > MAX_BACKUP_CONTENT:
                raise BadBackup(["The archive's contents are too large."])
            files[name] = tar.extractfile(m).read()
    if BACKUP_MANIFEST not in files:
        raise BadBackup([f"This is not a lineage backup ({BACKUP_MANIFEST} is missing)."])
    try:
        manifest = json.loads(files.pop(BACKUP_MANIFEST))
        assert isinstance(manifest, dict) and manifest.get("app") == "lineage" and isinstance(manifest.get("version"), str)
    except (ValueError, AssertionError):
        raise BadBackup([f"This is not a lineage backup ({BACKUP_MANIFEST} is not valid)."]) from None
    if "workspace.yaml" not in files:
        raise BadBackup(["The backup has no workspace.yaml."])
    try:
        yaml_text = files.pop("workspace.yaml").decode("utf-8")
        descriptions = {(n.split("/")[1], n.split("/")[2][:-3]): b.decode("utf-8") for n, b in files.items()}
    except UnicodeDecodeError:
        raise BadBackup(["The backup contains files that are not UTF-8 text."]) from None
    return manifest, yaml_text, descriptions


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(TMP_PREFIX + path.name)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def to_yaml(ws: M.Workspace) -> str:
    data = ws.model_dump(
        by_alias=True,
        exclude={t: {"__all__": {"description"}} for t in graph.TYPES},
    )
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True)


def descriptions(ws: M.Workspace | None) -> dict[tuple[str, str], str]:
    if ws is None:
        return {}
    return {
        (t, e.id): e.description
        for t in graph.TYPES
        for e in getattr(ws, t)
        if e.description
    }


class Store:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        self.history = self.dir / ".history"
        self.lock = threading.RLock()
        self.ws: M.Workspace | None = None
        self.errors: list[str] = []
        self.sig = None
        with self.lock:
            if not (self.dir / "workspace.yaml").exists():
                self.dir.mkdir(parents=True, exist_ok=True)
                self._write_files(seed.workspace(), None)
            self._load()

    # ------------------------------------------------------------ reading

    def _signature(self):
        sig = []
        for root, dirs, files in os.walk(self.dir):
            if Path(root) == self.dir and ".history" in dirs:
                dirs.remove(".history")
            for name in files:
                if name.startswith(TMP_PREFIX):
                    continue
                p = Path(root) / name
                try:
                    st = p.stat()
                except FileNotFoundError:
                    continue
                sig.append((str(p.relative_to(self.dir)), st.st_mtime_ns, st.st_size))
        return tuple(sorted(sig))

    def _load(self) -> None:
        self.sig = self._signature()
        self.ws, self.errors = None, []
        try:
            text = (self.dir / "workspace.yaml").read_text(encoding="utf-8")
        except OSError as e:
            self.errors = [f"workspace.yaml: {e}"]
            return
        descriptions = {}
        for t in graph.TYPES:
            d = self.dir / "descriptions" / t
            if d.is_dir():
                for f in d.glob("*.md"):
                    descriptions[(t, f.name[:-3])] = f.read_text(encoding="utf-8")
        self.ws, self.errors = parse_workspace(text, descriptions)

    def refresh(self) -> None:
        """Reload if any file under data/ (except .history) changed."""
        with self.lock:
            if self._signature() != self.sig:
                self._load()

    def read(self) -> M.Workspace:
        with self.lock:
            self.refresh()
            if self.errors:
                raise Broken(self.errors)
            return self.ws

    # ------------------------------------------------------------ writing

    def _write_files(self, new: M.Workspace, old: M.Workspace | None) -> None:
        atomic_write(self.dir / "workspace.yaml", to_yaml(new))
        old_d, new_d = descriptions(old), descriptions(new)
        for (t, eid), text in new_d.items():
            if old_d.get((t, eid)) != text:
                atomic_write(self.dir / "descriptions" / t / f"{eid}.md", text)
        for key in old_d.keys() - new_d.keys():
            (self.dir / "descriptions" / key[0] / f"{key[1]}.md").unlink(missing_ok=True)

    def snapshots(self) -> list[Path]:
        if not self.history.is_dir():
            return []
        return sorted(p for p in self.history.iterdir() if p.is_dir())

    def _snapshot(self) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        dest = self.history / stamp
        n = 1
        while dest.exists():
            dest = self.history / f"{stamp}-{n}"
            n += 1
        dest.mkdir(parents=True)
        for item in self.dir.iterdir():
            if item.name == ".history" or item.name.startswith(TMP_PREFIX):
                continue
            if item.is_dir():
                shutil.copytree(item, dest / item.name)
            else:
                shutil.copy2(item, dest / item.name)
        for old in self.snapshots()[:-KEEP_SNAPSHOTS]:
            shutil.rmtree(old)

    def mutate(self, fn):
        """Apply fn to a copy of the workspace, validate, snapshot, write."""
        with self.lock:
            self.refresh()
            if self.errors:
                raise Broken(self.errors)
            new = self.ws.model_copy(deep=True)
            result = fn(new)
            errs = graph.validate(new)
            if errs:
                raise graph.Invalid(errs)
            self._snapshot()
            self._write_files(new, self.ws)
            self.ws = new
            self.sig = self._signature()
            return result

    # ------------------------------------------------------------ backup / restore

    def _data_files(self) -> list[Path]:
        """workspace.yaml and the description files: everything a backup needs."""
        files = [self.dir / "workspace.yaml"]
        d = self.dir / "descriptions"
        if d.is_dir():
            files += sorted(p for p in d.rglob("*.md") if p.is_file() and not p.name.startswith(TMP_PREFIX))
        return files

    def backup(self) -> tuple[bytes, dict]:
        """A .tar.gz of the data folder (without .history), with a manifest
        recording the lineage version that made it."""
        manifest = {
            "app": "lineage",
            "format": BACKUP_FORMAT,
            "version": app_version(),
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        buf = io.BytesIO()
        with self.lock, tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(BACKUP_MANIFEST)
            body = json.dumps(manifest, indent=2).encode()
            info.size = len(body)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(body))
            for f in self._data_files():
                tar.add(f, arcname=f.relative_to(self.dir).as_posix(), recursive=False)
        return buf.getvalue(), manifest

    def restore(self, data: bytes, force: bool = False) -> dict:
        """Replace the whole data folder (except .history) with a backup.
        The current data is snapshotted first, so Undo reverts a restore."""
        manifest, yaml_text, descriptions = read_backup(data)
        if manifest["version"] != app_version() and not force:
            raise VersionMismatch(manifest["version"], app_version())
        _, errs = parse_workspace(yaml_text, descriptions)
        if errs:
            raise BadBackup(["The backup is not a valid workspace:", *errs])
        with self.lock:
            staging = self.dir / f"{TMP_PREFIX}restore"
            shutil.rmtree(staging, ignore_errors=True)
            (staging / "descriptions").mkdir(parents=True)
            (staging / "workspace.yaml").write_text(yaml_text, encoding="utf-8")
            for (t, eid), text in descriptions.items():
                (staging / "descriptions" / t).mkdir(exist_ok=True)
                (staging / "descriptions" / t / f"{eid}.md").write_text(text, encoding="utf-8")
            self._snapshot()
            for item in self.dir.iterdir():
                if item.name in (".history", staging.name):
                    continue
                shutil.rmtree(item) if item.is_dir() else item.unlink()
            for item in staging.iterdir():
                os.replace(item, self.dir / item.name)
            shutil.rmtree(staging)
            self._load()
        return manifest

    def undo(self) -> None:
        """Restore the most recent snapshot and drop it."""
        with self.lock:
            snaps = self.snapshots()
            if not snaps:
                raise NothingToUndo()
            snap = snaps[-1]
            for item in self.dir.iterdir():
                if item.name == ".history":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            for item in snap.iterdir():
                if item.is_dir():
                    shutil.copytree(item, self.dir / item.name)
                else:
                    shutil.copy2(item, self.dir / item.name)
            shutil.rmtree(snap)
            self._load()
