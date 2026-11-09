# Architecture

lineage is one Python process serving a single-page app, with plain files as its database.

```
browser ── Svelte 5 SPA ──(JSON over HTTP, cookie session)──▶ FastAPI (one uvicorn worker)
                                                                   │
                                                     Accounts ─────┤
                                                     Registry ── Store per user ──▶ data/users/<name>/
```

## Backend (`backend/`)

| Module | Role |
|---|---|
| `models.py` | the data model (Pydantic): stored entities, create/patch bodies, API responses |
| `graph.py` | pure functions over a workspace: derived data, validation, create/patch/delete rules, migrations of older formats |
| `store.py` | one workspace folder: loading, atomic writes, snapshots and undo, reloading after hand edits, backup and restore |
| `accounts.py` | `accounts.yaml`, password hashing, signed session cookies, login throttling, the per-user `Store` registry, the demo account |
| `app.py` | the HTTP routes, error mapping, the CSRF check |
| `manage.py` | the account command line |
| `seed.py` | the starter vocabulary of a new workspace |

### A change, step by step

1. The route checks the session cookie and picks the user's `Store` from the registry.
2. `Store.mutate` takes the store's lock, reloads from disk if any file changed (hand edits), and copies the workspace.
3. The change is applied to the copy with a function from `graph.py`, then the **whole** copy is validated. Any error aborts with 422 and nothing is written.
4. A snapshot of the current files goes to `.history/` (the last 20 are kept), then the new files are written atomically.

Undo restores the newest snapshot. Restoring a backup snapshots first, so it can be undone the same way.

### Why one worker

The lock that serialises writes lives in the process. Several workers or replicas on one data folder could interleave writes; lineage is meant to run as a single small process.

### Derived data

Nothing that can be computed is stored: milestone order, parents, heads, current states, time in state, merged and closed projects are all derived in `graph.derive` on every read. The files therefore cannot contradict themselves, and hand edits stay simple.

## Frontend (`frontend/`)

- **Svelte 5** (runes) with **Vite** and **TypeScript**.
- `src/api/`: `schema.d.ts`, generated from the backend's OpenAPI schema (never edited by hand), and `client.ts`, a small fetch wrapper.
- `src/state.svelte.ts`: shared UI state, the session, polling.
- `src/layout/`: pure, unit-tested functions that turn a workspace into geometry (lanes, scales, the dependency graph, colours, filters).
- `src/views/` and `src/components/`: the timeline (SVG with d3-zoom), status board, dependencies view (dagre), settings, side panel and forms.
- Descriptions are rendered with markdown-it and KaTeX, then sanitised with DOMPurify. The renderer and the dependencies view are loaded on first use, to keep the main bundle small.

The page polls `GET /api/workspace` every 5 seconds with `If-None-Match`; unchanged data costs a 304.
