"""Manage lineage accounts.

    python -m backend.manage list
    python -m backend.manage adduser NAME [--admin] [--adopt | --from DIR] [--password-stdin]
    python -m backend.manage admin NAME on|off
    python -m backend.manage passwd NAME [--password-stdin]
    python -m backend.manage deluser NAME [--purge]

The data folder is DATA_DIR (default /data), as for the server. In Docker:

    docker compose exec -it lineage python -m backend.manage adduser alice

The running server picks up changes within a moment; no restart needed.
"""

import argparse
import getpass
import os
import shutil
import sys
from pathlib import Path

from . import accounts as A


def read_password(from_stdin: bool, confirm: bool = True) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    pw = getpass.getpass("Password: ")
    if confirm and getpass.getpass("Repeat it: ") != pw:
        raise A.AccountError("The passwords do not match.")
    return pw


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m backend.manage", description="Manage lineage accounts.")
    ap.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "/data"), help="the data folder (default: $DATA_DIR or /data)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list the accounts (admins are marked)")

    p = sub.add_parser("adduser", help="create an account")
    p.add_argument("name")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--adopt", action="store_true",
                     help="move the single-user workspace in the data folder (from before accounts) to this user")
    src.add_argument("--from", dest="from_dir", metavar="DIR", help="start from a copy of this workspace folder (e.g. examples/papers)")
    p.add_argument("--admin", action="store_true",
                   help="make it an admin (the first account created while there is no admin becomes one anyway)")
    p.add_argument("--password-stdin", action="store_true", help="read the password from the first line of stdin")

    p = sub.add_parser("admin", help="make an account an admin, or a plain user again")
    p.add_argument("name")
    p.add_argument("state", choices=["on", "off"])

    p = sub.add_parser("passwd", help="set a password (ends that user's sessions)")
    p.add_argument("name")
    p.add_argument("--password-stdin", action="store_true", help="read the password from the first line of stdin")

    p = sub.add_parser("deluser", help="delete an account (its workspace folder is kept unless --purge)")
    p.add_argument("name")
    p.add_argument("--purge", action="store_true", help="also delete the user's workspace folder")

    args = ap.parse_args(argv)
    root = Path(args.data_dir)
    accounts = A.Accounts(root)

    try:
        if args.cmd == "list":
            for u in accounts.details():
                print(u["username"] + ("  (admin)" if u["admin"] else ""))
            return 0

        A.check_name(args.name)
        if args.cmd == "adduser":
            if accounts.get(args.name):
                raise A.AccountError(f"User {args.name!r} already exists.")
            dest = A.user_dir(root, args.name)
            if args.adopt:
                if not A.has_legacy_layout(root):
                    raise A.AccountError(f"There is no workspace.yaml in {root} to adopt.")
            if args.adopt or args.from_dir:
                if dest.exists() and any(dest.iterdir()):
                    raise A.AccountError(f"{dest} already exists and is not empty.")
            password = A.check_password(read_password(args.password_stdin))
            if args.adopt:
                A.adopt_legacy(root, args.name)
            elif args.from_dir:
                A.copy_workspace(Path(args.from_dir), dest)
            if args.admin and args.name == A.DEMO_NAME and password == A.DEMO_PASSWORD:
                raise A.AccountError("The demo account cannot be an admin while its password is 'demo'.")
            is_admin = accounts.add(args.name, password, admin=True if args.admin else None)
            where = "with the adopted workspace" if args.adopt else f"from {args.from_dir}" if args.from_dir else "with an empty workspace"
            print(f"Created {'admin' if is_admin else 'user'} {args.name!r} {where} ({dest}).")
        elif args.cmd == "admin":
            u = accounts.get(args.name)
            if u is None:
                raise A.AccountError(f"User {args.name!r} does not exist.")
            on = args.state == "on"
            if on and args.name == A.DEMO_NAME and A.verify_password(A.DEMO_PASSWORD, u.get("password", "")):
                raise A.AccountError("The demo account cannot be an admin while its password is 'demo'. Change it first: passwd demo")
            accounts.set_admin(args.name, on)
            print(f"{args.name!r} is {'now an admin' if on else 'no longer an admin'}.")
            if not accounts.admins():
                print("warning: there is no admin account left.", file=sys.stderr)
        elif args.cmd == "passwd":
            if not accounts.get(args.name):
                raise A.AccountError(f"User {args.name!r} does not exist.")
            accounts.set_password(args.name, read_password(args.password_stdin))
            print(f"Password of {args.name!r} changed; their open sessions have ended.")
        elif args.cmd == "deluser":
            accounts.remove(args.name)
            if not accounts.admins() and accounts.names():
                print("warning: there is no admin account left.", file=sys.stderr)
            dest = A.user_dir(root, args.name)
            if args.purge and dest.exists():
                shutil.rmtree(dest)
                print(f"Deleted user {args.name!r} and {dest}.")
            else:
                print(f"Deleted user {args.name!r}. Their workspace stays in {dest}.")
        return 0
    except A.AccountError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
