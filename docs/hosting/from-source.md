# Running it from source

Requirements: Python 3.12 or newer, Node.js 22.12 or newer, and `make`.

```sh
git clone https://github.com/gondoresearch/lineage.git && cd lineage
make install                       # backend into .venv, frontend into frontend/node_modules
make start                         # backend on :8000 and GUI on :5173, in the background
```

Open <http://localhost:5173> and log in as **demo** / **demo**.

## Make targets

| Command | What it does |
|---|---|
| `make install` | creates `.venv` and installs the backend (with test dependencies) and the frontend dependencies |
| `make start` | starts the backend (uvicorn, `127.0.0.1:8000`) and the GUI (Vite dev server, `localhost:5173`) in the background; waits until both answer |
| `make stop` | stops both, including their child processes |
| `make restart` | `stop`, then `start` |
| `make status` | whether each one is running |
| `make build` | builds the GUI for production into `frontend/dist`; the backend then serves it itself at <http://127.0.0.1:8000> |
| `make docs`, `make docs-serve` | build this documentation, or serve it with live reload (see [Contributing](../internals/contributing.md)) |

Logs and pid files are in `.run/`. Override the settings on the command line:

```sh
make start DATA_DIR=/tmp/lineage-test BACKEND_PORT=8001 GUI_PORT=5174
```

| Variable | Default |
|---|---|
| `DATA_DIR` | `./data` |
| `BACKEND_PORT` | `8000` |
| `GUI_PORT` | `5173` |

!!! tip "Dev server or built frontend?"
    The Vite dev server (`:5173`) reloads as you edit the frontend and forwards `/api` to the backend. For a setup closest to production, run `make build` once and use the backend alone at `:8000`.

## Without make

```sh
python -m venv .venv && .venv/bin/pip install -e "./backend[test]"
cd frontend && npm install && cd ..

DATA_DIR=./data .venv/bin/uvicorn --factory backend.app:create_app     # terminal 1
cd frontend && npm run dev                                              # terminal 2
```

The dev server forwards `/api` to `http://localhost:8000`; override it with `API_URL=http://host:port npm run dev`.
