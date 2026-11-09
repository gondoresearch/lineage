# Changelog

All notable changes to lineage. Versions follow `MAJOR.MINOR.PATCH`; while lineage is below 1.0, a minor version may change the data layout (the upgrade steps are then in [Upgrading](https://gondoresearch.github.io/lineage/hosting/upgrading/)).

## 0.2.1 (2026-11-09)

### Added

- **Admin accounts.** An admin gets a **Settings → Users** section to add users, set their passwords, delete them (optionally with their workspace), and download or restore a backup of their workspace. Admins cannot open other users' workspaces, and manage only non-admin accounts from the web.
- The first account created while there is no admin becomes an admin (never the demo account). `manage adduser --admin` and `manage admin NAME on|off` manage admins; `manage list` marks them.
- `GET /api/me` and `POST /api/login` report `admin`; new `/api/admin/users…` routes.

## 0.2.0 (2026-11-09)

**Changes the data layout.** Existing installations need one command after upgrading; see Upgrading.

### Added

- **Accounts.** Every user logs in and has a private workspace in `data/users/<name>/`. Passwords are stored as scrypt hashes; sessions are signed cookies valid for 30 days.
- **Demo account.** On the first start, a `demo` account (password `demo`) is created with a copy of the example data. Skip it with `LINEAGE_DEMO=0`.
- **Account command line**: `python -m backend.manage list | adduser | passwd | deluser`, including `adduser --adopt` to move a 0.1 workspace into an account and `adduser --from DIR` to start from a copy of a data folder.
- **Settings → Account**: change your own password; this logs out your other sessions.
- Login throttling, and a required `X-Lineage: 1` header on every request that changes data (cross-site request protection).
- `LINEAGE_SECURE_COOKIE=1` for installations served over HTTPS.
- A `Makefile` to run lineage from source: `make install | build | start | stop | restart | status`.
- This documentation site.

### Changed

- The data folder now holds `accounts.yaml`, `.secret` and `users/`; a workspace no longer sits at the top of the folder.
- The math renderer and the dependencies view load on first use: the main JavaScript bundle went from 685 kB to 243 kB.
- The Docker image includes the example data (for the demo account).

## 0.1.1 (2026-11-06)

- Version shown next to the logo; `GET /api/version`.
- Backup download (`.tar.gz` with a version manifest) and restore, with checks and Undo.

## 0.1.0 (2026-11-06)

First version: timeline, status board and dependencies view; editing of every entity; domains, closing kinds, per-line text and styling, markers; undo; hand edits picked up from disk; dark mode; Docker packaging.
