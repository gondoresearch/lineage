# Contributing

## Setup

```sh
make install          # .venv with the backend and its test dependencies; frontend/node_modules
make start            # backend :8000 + Vite dev server :5173 (see Running from source)
```

## Tests and checks

```sh
cd backend && ../.venv/bin/pytest        # backend: validation, derived data, delete rules, storage, accounts, API
cd frontend && npm test                  # frontend: layout, colours, lanes, scales, filters, views
cd frontend && npx tsc --noEmit -p .     # type check
make build                               # production build of the frontend
```

`TEST.md` in the repository is a manual test plan, section by section, for checking the app by hand before a release.

## Regenerating the API types

`frontend/src/api/schema.d.ts` is generated from the backend's OpenAPI schema; never edit it by hand. With the backend running on port 8000:

```sh
cd frontend && npm run gen-api
```

Do this after changing anything in `backend/models.py` or the routes.

## Documentation

This site is built with MkDocs and the Material theme from the `docs/` folder; `mkdocs.yml` is at the root of the repository.

```sh
make docs-install     # once: MkDocs into .venv
make docs-serve       # http://127.0.0.1:8001, reloads as you edit
make docs             # build into site/, failing on broken links
```

### Screenshots

The screenshots in `docs/assets/screenshots/` are taken by `docs/screenshots.py`: it runs lineage on a copy of the example data, drives it with Playwright and writes one PNG per screenshot, with the clock fixed so they only change when the app does. Retake them all after a visible change:

```sh
.venv/bin/pip install playwright      # once; uses /usr/bin/chromium if present,
                                      # else: .venv/bin/python -m playwright install chromium
make screenshots
```

Parts of the reference are generated from the code by `docs/hooks/generate.py`: a line `<!-- gen:fields Project -->` becomes the field table of that model, `<!-- gen:cli -->` the command-line help, and `<!-- gen:api -->` the endpoint list. Pushing to `main` publishes the site to GitHub Pages (`.github/workflows/docs.yml`).

## Releasing

1. Update the version in `backend/pyproject.toml` and `frontend/package.json` (and `package-lock.json`).
2. Move the *unreleased* section of `CHANGELOG.md` under the new version and date.
3. Run the tests, the build and the relevant sections of `TEST.md`.
4. Commit as `Release X.Y.Z` and tag it `vX.Y.Z`.
