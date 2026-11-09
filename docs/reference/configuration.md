# Configuration

lineage is configured with environment variables.

## Server

| Variable | Default | Effect |
|---|---|---|
| `DATA_DIR` | `/data` | The data folder: `accounts.yaml`, `.secret` and `users/`. Created if missing. Also used by the [command line](cli.md). |
| `LINEAGE_DEMO` | `1` | Create the showcase accounts on the first start, when `accounts.yaml` does not exist yet: `demo` / `demo` (papers) and `lineage` / `lineage` (this repository's history). `0` skips them. |
| `LINEAGE_EXAMPLES` | `<repo>/examples` | The folder holding the example data folders (`papers/`, `lineage/`) the showcase accounts are copied from. Set to `/app/examples` in the Docker image. |
| `LINEAGE_SECURE_COOKIE` | `0` | `1` marks the login cookie *Secure*: browsers send it over HTTPS only. Turn it on when lineage is served over HTTPS. |
| `FRONTEND_DIR` | `<repo>/frontend/dist` | The built frontend, served at `/` if the folder exists. Set to `/app/frontend/dist` in the Docker image. |

The server is started with uvicorn: `uvicorn --factory backend.app:create_app` (add `--host` and `--port` as needed). Run **one worker only**.

## Docker Compose

Read from `.env` next to `docker-compose.yml`, or from the environment:

| Variable | Default | Effect |
|---|---|---|
| `LINEAGE_UID`, `LINEAGE_GID` | `1000` | The user and group the container runs as; set them to `id -u` / `id -g` so files in `data/` stay yours. |
| `LINEAGE_DEMO` | `1` | Passed to the server (above). |
| `LINEAGE_SECURE_COOKIE` | `0` | Passed to the server (above). |

The host port is set in `docker-compose.yml` (`127.0.0.1:8080:8000`).

## Makefile

Given on the `make` command line, e.g. `make start DATA_DIR=/tmp/lineage-test`:

| Variable | Default | Effect |
|---|---|---|
| `DATA_DIR` | `./data` | The data folder for the backend. |
| `BACKEND_PORT` | `8000` | The backend's port (on `127.0.0.1`). |
| `GUI_PORT` | `5173` | The Vite dev server's port. |

## Frontend dev server

| Variable | Default | Effect |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Where the Vite dev server forwards `/api` (`make start` sets it from `BACKEND_PORT`). |
