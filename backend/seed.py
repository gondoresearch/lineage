"""Seed vocabulary written on first run."""

from . import models as M
from .graph import slugify

STATES = [
    ("drafting", "solid", "me"),
    ("revising", "solid", "me"),
    ("with co-authors", "dashed", "others"),
    ("under review", "dashed", "others"),
    ("paused", "dotted", "nobody"),
    ("accepted", "solid", "nobody"),
    ("published", "solid", "nobody"),
]

KINDS = [
    ("draft", "open-circle", "drafting"),
    ("preprint", "star", None),
    ("submitted", "triangle", "under review"),
    ("revision", "diamond", "under review"),
    ("accepted", "filled-circle", "accepted"),
    ("published", "filled-star", "published"),
    ("rejected", "cross", "revising"),
    ("closed", "filled-square", None),
]

REFTYPES = [
    ("builds on", True, "dashed"),
    ("companion", False, "dotted"),
]


def workspace() -> M.Workspace:
    return M.Workspace(
        states=[
            M.State(id=slugify(n, "state"), name=n, line=line, waiting_on=w)
            for n, line, w in STATES
        ],
        kinds=[
            M.Kind(
                id=slugify(n, "kind"),
                name=n,
                shape=shape,
                default_state=slugify(d, "state") if d else None,
                closes=n == "closed",
            )
            for n, shape, d in KINDS
        ],
        reftypes=[
            M.RefType(id=slugify(n, "reftype"), name=n, directed=d, line=line)
            for n, d, line in REFTYPES
        ],
    )
