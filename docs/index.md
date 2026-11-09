# lineage

lineage is a small, self-hosted tool that **generalises the git workflow** — branches, commits, forks and merges, plus states and typed references — to any line of work. Each project is a branch, drawn as a lane on a timeline; its milestones are its commits. A project can fork from another project's milestone, merge into another project, or refer to work it builds on.

It started as a manager for papers and theses: "commits" are versions of a paper produced at a meeting or a date, "preprint" and "submitted" are milestones of their own, and reviews are states the paper waits in. Nothing in the model is tied to that domain, though — kinds of milestones, states, reference types and markers are all your own vocabulary.

All data lives in **plain files** (one YAML file plus Markdown descriptions per user) that you can read, edit by hand, back up and keep in git.

!!! warning "Preliminary, and heavily AI-assisted"
    lineage is a work in progress; features and the data format may still change between minor versions (see the [changelog](changelog.md)). Most of its code, tests and documentation were written by an AI coding assistant (Claude, by Anthropic), directed and reviewed by a human. Read the code before relying on it, and keep backups of your data.

## Where to go next

<div class="grid cards" markdown>

- **Try it** — [Getting started](getting-started.md): run it, log in as the demo user, and walk through the example.
- **Use it** — [Concepts](guide/concepts.md) explains projects, milestones, forks, merges and states; the rest of *Using lineage* covers each view.
- **Host it** — [Docker](hosting/docker.md) or [from source](hosting/from-source.md), then [accounts](hosting/accounts.md) and [HTTPS](hosting/https.md).
- **Look things up** — the [data format](reference/data-format.md), [configuration](reference/configuration.md), [command line](reference/cli.md) and [HTTP API](reference/api.md).

</div>

## At a glance

- **Timeline** of lanes per project, grouped, with forks drawn under their origin; pan, zoom, time axis or event order.
- **Status board** sorting projects by who they are waiting on and for how long; **dependencies view** as a graph.
- **Editing** of everything from a side panel, with confirmations that list what a delete would remove, and **undo** for every change.
- **Accounts**, each with a private workspace; **backup and restore** as a single file.
- **Hand edits** to the files on disk appear in the page within about 5 seconds.
- Runs offline: no external services, one small container.
