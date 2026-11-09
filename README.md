# lineage

> **Preliminary.** lineage is a work in progress; features and the data format may still change.
>
> **Heavily AI-assisted.** lineage is my first try at AI-assisted coding; most of the code, tests and documentation in this repository were written by an AI coding assistant (Claude, by Anthropic), directed and reviewed by a human. Treat it accordingly: read the code before relying on it, and keep backups of your data.

lineage is a small, self-hosted tool that **generalises the git workflow**: branches, commits, forks and merges, plus states and typed references between lines of work. Each project is a branch, drawn as a lane on a timeline; its milestones are its commits. A project can fork from another project's milestone, merge into another project, or refer to work it builds on.

Initially I intended lineage to become a manager for my papers and theses; quite soon I realized it could be a method for graphically illustrating projects and workflows based on milestones, relationships and dependencies. The git workflow maps onto a paper's development cycle: "commits" are versions of the paper produced by authors at specific dates or meetings, "preprints" are self-published versions, "submitted" is self-explanatory. Talking to friends in other areas I noticed that their workflow was quite like this one, so nothing in the model is tied to a particular domain: kinds, states, reference types and markers are all yours to define.

All data lives in plain files (one YAML file plus Markdown descriptions per user) that you can read, edit by hand, back up and version.

**📖 Documentation: https://gondoresearch.github.io/lineage/**

## Quick start

With Docker:

```sh
mkdir data
docker compose up -d                 # then open http://localhost:8080
```

From source (Python 3.12+, Node.js 22.12+):

```sh
make install
make start                           # then open http://localhost:5173; `make stop` to stop
```

Log in as **demo** / **demo** (research papers) or **lineage** / **lineage** (lineage's own history, in GitHub words) to explore. The **admin** account (password **admin**, which you must change at the first login) manages the other accounts in **Settings → Users**. Or create accounts from the command line:

```sh
docker compose exec -it lineage python -m backend.manage adduser NAME      # Docker
DATA_DIR=./data .venv/bin/python -m backend.manage adduser NAME            # from source
```

**Upgrading from 0.1?** Your workspace must be moved into an account once: `… manage adduser NAME --adopt`. See [Upgrading](https://gondoresearch.github.io/lineage/hosting/upgrading/).

## Documentation

- [Getting started](https://gondoresearch.github.io/lineage/getting-started/) — a ten-minute tour
- [Concepts](https://gondoresearch.github.io/lineage/guide/concepts/) — projects, milestones, forks, merges, states, references
- Hosting: [Docker](https://gondoresearch.github.io/lineage/hosting/docker/), [from source](https://gondoresearch.github.io/lineage/hosting/from-source/), [accounts](https://gondoresearch.github.io/lineage/hosting/accounts/), [HTTPS](https://gondoresearch.github.io/lineage/hosting/https/)
- Reference: [data format](https://gondoresearch.github.io/lineage/reference/data-format/), [configuration](https://gondoresearch.github.io/lineage/reference/configuration/), [command line](https://gondoresearch.github.io/lineage/reference/cli/), [HTTP API](https://gondoresearch.github.io/lineage/reference/api/)
- [Contributing](https://gondoresearch.github.io/lineage/internals/contributing/) and the [changelog](CHANGELOG.md)

The documentation sources are in [`docs/`](docs/); build them locally with `make docs-install && make docs-serve`.

## Security

lineage has accounts, but speaks plain HTTP and is published on `127.0.0.1` only. Before reaching it from other machines, put it behind an HTTPS reverse proxy, set `LINEAGE_SECURE_COOKIE=1`, and delete or re-password the showcase accounts (demo, lineage). See [HTTPS and exposing it](https://gondoresearch.github.io/lineage/hosting/https/) and the [security model](https://gondoresearch.github.io/lineage/internals/security/).

## License

lineage is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/) (CC BY-SA 4.0); the full text is in [`LICENSE`](LICENSE). You may share and adapt it, including commercially, as long as you give appropriate credit and distribute your adaptations under the same license.
