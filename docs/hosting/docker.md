# Running it with Docker

Requirements: Docker with Compose. Nothing else is needed on the machine, and the running app needs no internet access.

```sh
git clone https://github.com/gondoresearch/lineage.git && cd lineage
mkdir data
docker compose up -d              # builds the image the first time
```

Open <http://localhost:8080> and log in as **demo** / **demo** or **lineage** / **lineage** (see [the showcase accounts](accounts.md#the-demo-account)). Then create your own account:

```sh
docker compose exec -it lineage python -m backend.manage adduser alice
```

Your data lives in `./data` next to `docker-compose.yml`, one folder per user (see [Data format](../reference/data-format.md)).

## Before the first start

**Create `data/` yourself.** If Docker creates it, it belongs to root and lineage cannot write to it.

### Your user

The container runs as user and group id 1000, so that the files in `data/` stay yours. If `id -u` or `id -g` print something else, put your ids in a `.env` file next to `docker-compose.yml`; Compose reads it automatically:

```sh
printf 'LINEAGE_UID=%s\nLINEAGE_GID=%s\n' $(id -u) $(id -g) > .env
```

## The compose file

This is the `docker-compose.yml` in the repository, the one `docker compose up` uses:

```yaml title="docker-compose.yml"
--8<-- "docker-compose.yml"
```

It is made for using lineage on your own machine. For a server that other machines reach, use the [HTTPS example](https.md#complete-example-with-docker-compose) instead.

## Day to day

| Task | Command |
|---|---|
| Logs | `docker compose logs -f` |
| Stop | `docker compose down` (your data stays in `data/`) |
| Update after pulling new code | `docker compose up -d --build`, then read [Upgrading](upgrading.md); the new version is built as a new image, `lineage:X.Y.Z` |
| Go back to an earlier version | check out its tag (`git checkout v0.3.0`) and `docker compose up -d`: its image is still there (`docker image ls lineage`); restore a backup if the data format changed |
| Manage accounts | `docker compose exec -it lineage python -m backend.manage …` ([Accounts](accounts.md)) |

The container restarts on its own after a reboot (`restart: unless-stopped`).

## Reaching it from other machines

The port is published on `127.0.0.1` only, because lineage speaks plain HTTP and passwords would cross the network unencrypted. To use it from other machines, put it behind a reverse proxy that does HTTPS: see [HTTPS and exposing it](https.md), which has a [complete compose file](https.md#complete-example-with-docker-compose) with Caddy.

## Options

Set these in `.env` (or the environment of `docker compose`); all are described in [Configuration](../reference/configuration.md).

| Variable | Default | Effect |
|---|---|---|
| `LINEAGE_UID`, `LINEAGE_GID` | `1000` | the user and group the container runs as |
| `LINEAGE_DEMO` | `1` | `0`: do not create the showcase accounts (demo, lineage) on the first start |
| `LINEAGE_SECURE_COOKIE` | `0` | `1`: send the login cookie over HTTPS only |

## The image

The image is built in two stages: Node builds the frontend, then a `python:3.13-slim` image installs the backend and serves the built frontend from a single uvicorn worker on port 8000. It includes the example data, used for the showcase accounts.
