# Changelog

All notable changes to lineage. Versions follow `MAJOR.MINOR.PATCH`; while lineage is below 1.0, a minor version may change the data layout (the upgrade steps are then in [Upgrading](https://gondoresearch.github.io/lineage/hosting/upgrading/)).

## Unreleased

### Added

- **Default admin:** whenever there is no admin, lineage creates `admin` / `admin`, which must choose a new password before anything else works.

### Changed

- Docker: the image is tagged with the version (`lineage:0.3.1`), so each version is its own image and older ones stay available.

## 0.3.1 (2026-11-09)

### Added

- **Collapse days** (timeline, Days): each project's milestones of one day are drawn as one mark with a **×n** badge; clicking it lists them (symbol, kind, state, time) in the side panel.

### Changed

- In Days, zooming in stops at days (and the axis never shows times of day); in Hours, at minutes.
- The lineage showcase account no longer has a *merge* kind: merge commits are commits that merge a pull request (the history already says they are merges).

## 0.3.0 (2026-11-09)

**Changes the data format** (read automatically; see Upgrading).

### Added

- **Timestamps.** Milestones have a date and a time (`at: 2026-11-09T14:30`); new ones start at the current time, editable. References record when they were made (`created`).
- **Days / Hours** switch on the timeline: by day (as before) or at the time of day, with "now" and hour labels when zoomed in.
- A second showcase account, **lineage** / **lineage**: lineage's own history in GitHub words (branches, commits, pull requests, merges, releases) with their real times. The **demo** account is back to papers only.
- Screenshots throughout the documentation, taken by `make screenshots` (`docs/screenshots.py`, Playwright).

### Changed

- Same-day milestones: their order within a day follows history across projects, so a fork drawn on the day of its origin starts to the right of it, and a merge lands to the right of what it merges. In *Time*, close milestones never overlap: crowded stretches are spread out just enough (less in a narrow window), the date axis follows them and gains finer labels where it is stretched, and zooming in restores exact times.
- The timeline can zoom in much further (to read minutes).
- The API: milestones use `at` instead of `date` (a `date` alone is still accepted: midnight).

### Fixed

- Settings: long domain names no longer push the group reorder buttons out of the list; counts say "1 project" rather than "1 projects".
- Settings → Users: the table's action buttons no longer break its layout.
- Opening the side panel no longer pushes the start of the timeline out of view.

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
