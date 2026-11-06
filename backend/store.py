"""Loading and saving the data folder: atomic writes, snapshots, undo, and
reloading after hand edits."""

import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import ValidationError

from . import graph, seed
from . import models as M

KEEP_SNAPSHOTS = 20
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
            raw = yaml.load((self.dir / "workspace.yaml").read_text(encoding="utf-8"), Loader=_Loader)
        except (OSError, yaml.YAMLError) as e:
            self.errors = [f"workspace.yaml: {e}"]
            return
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            self.errors = ["workspace.yaml: the top level must be a mapping."]
            return
        try:
            ws = M.Workspace.model_validate(raw)
        except ValidationError as e:
            self.errors = [f"workspace.yaml: {m}" for m in graph.pydantic_messages(e)]
            return
        for t in graph.TYPES:
            d = self.dir / "descriptions" / t
            entities = graph.by_id(ws, t)
            if d.is_dir():
                for f in d.glob("*.md"):
                    e = entities.get(f.name[:-3])
                    if e is not None:
                        e.description = f.read_text(encoding="utf-8")
        errs = graph.validate(ws)
        if errs:
            self.errors = errs
            return
        self.ws = ws

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
