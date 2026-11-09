# Concepts

lineage borrows git's model of history and adds what git does not record: what happens *between* commits, and how separate lines of work relate.

## The pieces

| Term | Meaning | git equivalent |
|---|---|---|
| **Workspace** | everything a user has: all of the below | repository |
| **Domain** | an optional top-level area that groups are drawn under | none |
| **Group** | a set of projects drawn together (e.g. a research thread) | closest: a branch namespace such as `feature/*` |
| **Project** | a line of work (e.g. a paper) | branch |
| **Milestone** | a step in a project, with a date and time | commit |
| **Fork** | a project started from a milestone of another project | a branch created from a commit |
| **Merge** | a milestone that brings in milestones of other projects | merge commit |
| **Head** | a project's latest milestone that has happened | branch tip |
| **Planned milestone** | a milestone that has not happened yet | none: git has no future commits |
| **State** | the condition a project is in from one milestone until the next (drafting, under review…) | none |
| **Reference** | a typed link between milestones of different projects (builds on, companion…) | closest: a commit message citing another commit |
| **Kind** | the type of a milestone (draft, submitted, published…), shown as its symbol | closest: a Conventional Commits type (`feat:`, `fix:`) |
| **Marker** | a flag on milestones (warning, open question…) | closest: a tag |

<figure markdown="span">
  [![The **lineage** showcase account: this repository's history. Each feature branch forks from *main*, gets commits (dots) and a pull request (triangle), and is merged back into *main* by a merge commit (a commit that merges it: the brown curve); releases are diamonds. Dashed arrows are *depends on* references; faded symbols are planned.](../assets/screenshots/timeline-lineage.png)](../assets/screenshots/timeline-lineage.png)
  <figcaption>The **lineage** showcase account: this repository's history. Each feature branch forks from *main*, gets commits (dots) and a pull request (triangle), and is merged back into *main* by a merge commit (a commit that merges it: the brown curve); releases are diamonds. Dashed arrows are *depends on* references; faded symbols are planned.</figcaption>
</figure>

## What is derived, never stored

lineage stores as little as possible and computes the rest, so the files stay simple and cannot contradict themselves:

- Within a project, milestones are ordered by **date and time**, then by the order they were created; each one's parent is the previous one.
- A project is a **fork** if its `from` points at a milestone of another project. A milestone is a **merge** if its `merges` lists milestones of other projects.
- A project's **head** is its latest non-planned milestone. Its **current state** is the head's state, and its **time in state** is today minus the head's date.
- A project whose head is merged into another project is **merged**. A project whose head has a kind that *closes* the project (such as "closed") ends there and has no state.

## States: who is the project waiting on?

Each state says who the project is waiting on while it is in that state: **me**, **others** or **nobody**. That drives the [status board](status-and-deps.md): "drafting" waits on you, "under review" on others, "paused" or "published" on nobody (inactive).

A milestone's kind can suggest a **default state**: choosing the kind "submitted" for a new milestone preselects "under review".

## Your own vocabulary

Kinds, states, reference types, markers, domains and groups are all yours to define in **Settings** — see [Vocabulary](vocabulary.md). The starter vocabulary a new account gets happens to describe papers; replace it with whatever your work looks like.

## Descriptions

Every entity can have a **description** in Markdown, with LaTeX math: `$…$` inline and `$$…$$` on its own line. Descriptions are stored as separate `.md` files, one per entity, so they are easy to edit by hand.

## Accounts

Each account has its own workspace. Nothing is shared between accounts; see [Accounts](../hosting/accounts.md).
