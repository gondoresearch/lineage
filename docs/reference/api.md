# HTTP API

The frontend talks to the backend over a small JSON API, which you can use too. While the backend runs, interactive documentation is at `/docs` (it loads its scripts from a CDN, so it needs internet) and the schema at `/openapi.json`.

## Authentication

1. `POST /api/login` with `{"username": "...", "password": "..."}` sets the session cookie `lineage_session` and returns `{"username": "..."}`.
2. Send that cookie with every request. Without it (or with an expired or revoked one), every route except `/api/login` and `/api/version` answers **401** `{"errors": ["Not logged in."]}`.
3. Every request that is not `GET`, `HEAD` or `OPTIONS` must carry the header **`X-Lineage: 1`**, or it is refused with **403**. This protects against requests forged by other websites.

Failed logins answer **401**; after 5 failures in a row the answer is **429** with a `Retry-After` header.

```sh
curl -c cookies -X POST localhost:8000/api/login \
     -H 'X-Lineage: 1' -H 'Content-Type: application/json' \
     -d '{"username": "demo", "password": "demo"}'
curl -b cookies localhost:8000/api/workspace
curl -b cookies -X PATCH localhost:8000/api/groups/teaching \
     -H 'X-Lineage: 1' -H 'Content-Type: application/json' -d '{"name": "Courses"}'
```

## Conventions

- `GET /api/workspace` returns the whole workspace plus derived data (heads, current states, merged projects…). It sends an `ETag`; repeat with `If-None-Match` to get `304 Not Modified` when nothing changed. The page polls it every 5 seconds this way.
- Entities are created with `POST /api/<type>`, changed with `PATCH /api/<type>/<id>` (only the fields sent), and deleted with `DELETE /api/<type>/<id>`.
- `DELETE …?dry_run=true` changes nothing and returns what would be removed (`removes`) and what blocks the delete (`blockers`); a real delete that is blocked answers **409** with the blockers.
- Errors have the form `{"errors": ["message", ...]}`: **404** for an unknown id, **422** for an invalid request or a change that would leave the workspace inconsistent.
- `POST /api/undo` reverts the last change (**409** if there is nothing to undo).
- `GET /api/backup` returns a `.tar.gz`; `POST /api/restore` takes one as the request body (`Content-Type: application/gzip`), with `?force=true` to restore a backup from another lineage version.

## Endpoints

Generated from the backend's OpenAPI schema:

<!-- gen:api -->
