# Data format

All data is plain text. You can read it, edit it by hand while lineage runs, back it up and keep it in git.

## The data folder

```
data/
  accounts.yaml                     user names and password hashes (scrypt)
  .secret                           the key that signs login cookies
  users/<name>/                     one workspace per user:
    workspace.yaml                  all entities except descriptions
    descriptions/<type>/<id>.md     one Markdown file per entity that has a description
    .history/<timestamp>/           snapshots taken before each change (the last 20), used by Undo
```

`<type>` is one of `domains`, `groups`, `projects`, `milestones`, `references`, `kinds`, `states`, `reftypes`, `markers`.

- **Writing:** every change is validated against the whole workspace before anything is written, and files are written atomically (to a temporary file, then renamed).
- **Hand edits** are picked up within about 5 seconds. If a hand edit leaves the workspace invalid, the page lists the problems until the file is fixed. Comments in `workspace.yaml` are not kept when lineage writes it.
- **Ids** are made from the name or title when an entity is created (`Spectral filters` → `spectral-filters`, with a numeric suffix if taken) and never change, so renaming is safe. A milestone's id is `<project id>.<slug of its title>`.
- **Colours** are `#RRGGBB` strings; `null` means the theme's neutral colour.
- **Deleting `.secret`** logs everybody out; a new one is created on the next start.

## `workspace.yaml`

The top level has `settings` and one list per entity type:

```yaml
settings:
  fork_color: '#7f7f7f'
  merge_color: '#8c564b'
  fork_width: 1.8
  merge_width: 1.8
domains: [...]
groups: [...]
projects: [...]
milestones: [...]
references: [...]
kinds: [...]
states: [...]
reftypes: [...]
markers: [...]
```

A short example of the main entities:

```yaml
groups:
- id: graph-learning
  name: Graph learning
  domain: research
  color: '#4c72b0'
projects:
- id: spectral-filters
  title: Spectral filters for graph networks
  group: graph-learning
  from: null                                # or a milestone id: a fork
milestones:
- id: spectral-filters.first-draft
  project: spectral-filters
  title: First draft
  date: 2025-03-14
  kind: draft
  state: drafting
- id: spectral-filters.submitted
  project: spectral-filters
  title: Submitted to the conference
  date: 2025-05-02
  kind: submitted
  state: under-review
references:
- id: builds-on
  type: builds-on
  from: spectral-filters-journal.first-draft
  to: spectral-filters.submitted
```

`examples/papers/workspace.yaml` in the repository is a complete example that uses every feature.

The tables below are generated from the code (`backend/models.py`).

### Settings

<!-- gen:fields Settings -->

### Domain

<!-- gen:fields Domain -->

### Group

<!-- gen:fields Group -->

### Project

<!-- gen:fields Project -->

`from` is a milestone id of another project: the project is a fork of that milestone.

### Milestone

<!-- gen:fields Milestone -->

`merges` lists milestone ids of other projects that this milestone merges in. `state: null` is only valid for a kind that closes the project.

### Link

<!-- gen:fields Link -->

### Reference

<!-- gen:fields Reference -->

### Kind

<!-- gen:fields Kind -->

### State

<!-- gen:fields State -->

### RefType

<!-- gen:fields RefType -->

### Marker

<!-- gen:fields Marker -->

## Descriptions

A description is stored in `descriptions/<type>/<id>.md`, not in `workspace.yaml`; it is Markdown with `$…$` and `$$…$$` math. Deleting the file removes the description; an entity with no file has no description.

## `accounts.yaml`

```yaml
users:
  alice:
    password: scrypt$16384$8$1$<salt>$<hash>
    epoch: 2
    created: '2026-11-09T12:00:00+00:00'
```

`epoch` increases with every password change; sessions issued under an older epoch are no longer valid. Use the [command line](cli.md) rather than editing this file; if you do edit it and make it invalid, nobody can log in until it is fixed (the log says why).
