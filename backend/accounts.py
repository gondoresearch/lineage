"""User accounts: accounts.yaml, password hashing, signed session cookies,
login throttling, the demo account, and one Store per user folder.

Layout of the data folder:

    accounts.yaml      users and their password hashes (safe to edit by hand)
    .secret            the key that signs session cookies
    users/<name>/      that user's workspace (an ordinary lineage data folder)
"""

import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .store import Store, atomic_write

log = logging.getLogger("lineage")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
MIN_PASSWORD = 8
SESSION_DAYS = 30
SESSION_SECONDS = SESSION_DAYS * 24 * 3600
COOKIE = "lineage_session"
DEMO_NAME = "demo"
DEMO_PASSWORD = "demo"

# scrypt parameters: ~16 MiB of memory, well under a tenth of a second.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


class AccountError(Exception):
    """A bad account operation (unknown user, invalid name, short password…)."""


def check_name(name: str) -> str:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise AccountError(
            f"Invalid user name {name!r}: use 1 to 32 lowercase letters, digits, '-' or '_', starting with a letter or digit."
        )
    return name


def check_password(password: str) -> str:
    if len(password) < MIN_PASSWORD:
        raise AccountError(f"The password must have at least {MIN_PASSWORD} characters.")
    return password


# ------------------------------------------------------------------ passwords


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        return hmac.compare_digest(_scrypt(password, _unb64(salt), int(n), int(r), int(p)), _unb64(digest))
    except (ValueError, TypeError):
        return False


# Checked against when the user does not exist, so timing does not reveal names.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


# ------------------------------------------------------------------ accounts.yaml


class Accounts:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "accounts.yaml"
        self.lock = threading.RLock()
        self.users: dict[str, dict] = {}
        self.sig = None
        self._secret: bytes | None = None

    def exists(self) -> bool:
        return self.path.exists()

    def _signature(self):
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def refresh(self) -> None:
        """Reload accounts.yaml if it changed on disk (e.g. after a CLI command)."""
        with self.lock:
            sig = self._signature()
            if sig == self.sig:
                return
            self.sig = sig
            if sig is None:
                self.users = {}
                return
            try:
                raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
                users = raw.get("users") or {}
                if not isinstance(users, dict):
                    raise ValueError("'users' must be a mapping")
                self.users = {
                    check_name(str(name)): dict(u) for name, u in users.items() if isinstance(u, dict)
                }
            except (OSError, ValueError, yaml.YAMLError, AccountError, AttributeError) as e:
                # Fail closed: nobody can log in until the file is fixed.
                log.error("accounts.yaml is invalid, no one can log in until it is fixed: %s", e)
                self.users = {}

    def _save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        text = "# lineage accounts. Manage them with: python -m backend.manage --help\n" + yaml.safe_dump(
            {"users": self.users}, sort_keys=True, allow_unicode=True
        )
        atomic_write(self.path, text)
        self.sig = self._signature()

    def names(self) -> list[str]:
        with self.lock:
            self.refresh()
            return sorted(self.users)

    def get(self, name: str) -> dict | None:
        with self.lock:
            self.refresh()
            return self.users.get(name)

    def add(self, name: str, password: str, *, enforce_length: bool = True) -> None:
        check_name(name)
        if enforce_length:
            check_password(password)
        with self.lock:
            self.refresh()
            if name in self.users:
                raise AccountError(f"User {name!r} already exists.")
            self.users[name] = {
                "password": hash_password(password),
                "epoch": 1,
                "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            self._save()

    def set_password(self, name: str, password: str) -> None:
        """Change a password. Bumps the epoch, so every existing session of the user ends."""
        check_password(password)
        with self.lock:
            self.refresh()
            u = self.users.get(name)
            if u is None:
                raise AccountError(f"User {name!r} does not exist.")
            u["password"] = hash_password(password)
            u["epoch"] = int(u.get("epoch", 1)) + 1
            self._save()

    def remove(self, name: str) -> None:
        with self.lock:
            self.refresh()
            if name not in self.users:
                raise AccountError(f"User {name!r} does not exist.")
            del self.users[name]
            self._save()

    def check(self, name: str, password: str) -> bool:
        u = self.get(name) if NAME_RE.match(name or "") else None
        ok = verify_password(password, u["password"] if u else _DUMMY_HASH)
        return ok and u is not None

    # -------------------------------------------------------------- sessions

    def secret(self) -> bytes:
        with self.lock:
            if self._secret is None:
                p = self.root / ".secret"
                if not p.exists():
                    self.root.mkdir(parents=True, exist_ok=True)
                    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w") as f:
                        f.write(secrets.token_hex(32))
                self._secret = bytes.fromhex(p.read_text().strip())
            return self._secret

    def _sign(self, payload: str) -> str:
        return _b64(hmac.new(self.secret(), payload.encode(), hashlib.sha256).digest())

    def make_session(self, name: str, now: float | None = None) -> str:
        u = self.get(name)
        if u is None:
            raise AccountError(f"User {name!r} does not exist.")
        payload = f"{name}|{int(u.get('epoch', 1))}|{int(now if now is not None else time.time())}"
        return f"{_b64(payload.encode())}.{self._sign(payload)}"

    def session_user(self, cookie: str | None, now: float | None = None) -> str | None:
        """The user a session cookie belongs to, or None if it is invalid, expired or revoked."""
        if not cookie or "." not in cookie:
            return None
        try:
            p64, sig = cookie.split(".", 1)
            payload = _unb64(p64).decode()
            name, epoch, issued = payload.split("|")
            epoch, issued = int(epoch), int(issued)
        except (ValueError, UnicodeDecodeError):
            return None
        if not hmac.compare_digest(sig, self._sign(payload)):
            return None
        now = now if now is not None else time.time()
        if not (issued - 60 <= now < issued + SESSION_SECONDS):
            return None
        u = self.get(name)
        if u is None or int(u.get("epoch", 1)) != epoch:
            return None
        return name


# ------------------------------------------------------------------ throttling


class Throttle:
    """After FREE failed logins for a (user, address), lock it out for BASE
    seconds, doubling with every further failure. A success resets it."""

    FREE = 5
    BASE = 30
    MAX = 3600

    def __init__(self):
        self.lock = threading.Lock()
        self.state: dict[tuple[str, str], tuple[int, float]] = {}

    def wait(self, key: tuple[str, str], now: float | None = None) -> int:
        """Seconds until another attempt is allowed (0: allowed now)."""
        now = now if now is not None else time.monotonic()
        with self.lock:
            _, until = self.state.get(key, (0, 0.0))
            return max(0, int(until - now + 0.999))

    def failed(self, key: tuple[str, str], now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        with self.lock:
            n, _ = self.state.get(key, (0, 0.0))
            n += 1
            until = now + min(self.MAX, self.BASE * 2 ** (n - self.FREE)) if n >= self.FREE else 0.0
            self.state[key] = (n, until)
            if len(self.state) > 10_000:  # keep memory bounded
                self.state.pop(next(iter(self.state)))

    def succeeded(self, key: tuple[str, str]) -> None:
        with self.lock:
            self.state.pop(key, None)


# ------------------------------------------------------------------ per-user stores


def user_dir(root: Path, name: str) -> Path:
    return Path(root) / "users" / check_name(name)


class Registry:
    """One Store per user, created on first use."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.stores: dict[str, Store] = {}

    def get(self, name: str) -> Store:
        d = user_dir(self.root, name)
        with self.lock:
            s = self.stores.get(name)
            # The folder may have been removed (deluser --purge) and the user re-added.
            if s is None or not (d / "workspace.yaml").exists():
                s = self.stores[name] = Store(d)
            return s


# ------------------------------------------------------------------ setup helpers


def default_examples() -> Path:
    return Path(os.environ.get("LINEAGE_EXAMPLES", Path(__file__).resolve().parent.parent / "examples" / "papers"))


def copy_workspace(src: Path, dest: Path) -> None:
    """Copy a workspace folder (workspace.yaml and descriptions/, not .history) into dest."""
    src = Path(src)
    if not (src / "workspace.yaml").is_file():
        raise AccountError(f"{src} is not a lineage data folder (no workspace.yaml).")
    if dest.exists() and any(dest.iterdir()):
        raise AccountError(f"{dest} already exists and is not empty.")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "workspace.yaml", dest / "workspace.yaml")
    if (src / "descriptions").is_dir():
        shutil.copytree(src / "descriptions", dest / "descriptions")


LEGACY_ITEMS = ("workspace.yaml", "descriptions", ".history")


def has_legacy_layout(root: Path) -> bool:
    return (Path(root) / "workspace.yaml").exists()


def adopt_legacy(root: Path, name: str) -> None:
    """Move a pre-accounts workspace (data/workspace.yaml…) into users/<name>/."""
    root = Path(root)
    dest = user_dir(root, name)
    if not has_legacy_layout(root):
        raise AccountError(f"There is no workspace.yaml in {root} to adopt.")
    if dest.exists() and any(dest.iterdir()):
        raise AccountError(f"{dest} already exists and is not empty.")
    dest.mkdir(parents=True, exist_ok=True)
    for item in LEGACY_ITEMS:
        if (root / item).exists():
            os.replace(root / item, dest / item)


def bootstrap(root: Path, accounts: Accounts) -> None:
    """First start: create the demo account (unless LINEAGE_DEMO=0). Warn
    about an old single-user layout and about the demo password."""
    root = Path(root)
    if not accounts.exists() and os.environ.get("LINEAGE_DEMO", "1") != "0":
        dest = user_dir(root, DEMO_NAME)
        examples = default_examples()
        if not dest.exists() and (examples / "workspace.yaml").is_file():
            copy_workspace(examples, dest)
        elif not dest.exists():
            log.warning("Example data not found at %s; the demo user starts with an empty workspace.", examples)
        accounts.add(DEMO_NAME, DEMO_PASSWORD, enforce_length=False)
        log.warning("Created the demo account (user 'demo', password 'demo').")
    if has_legacy_layout(root):
        log.warning(
            "%s holds a workspace from before accounts existed. Move it to a user with: "
            "python -m backend.manage adduser NAME --adopt",
            root,
        )
    demo = accounts.get(DEMO_NAME)
    if demo and verify_password(DEMO_PASSWORD, demo.get("password", "")):
        log.warning(
            "The demo account still has the password 'demo'. Change it or delete it before exposing lineage: "
            "python -m backend.manage passwd demo | deluser demo"
        )
    if not accounts.names():
        log.warning("There are no accounts. Create one with: python -m backend.manage adduser NAME")
