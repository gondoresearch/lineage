"""Derived quantities, validation, entity operations and delete rules.

Everything here is pure: functions take a Workspace and either return values
or mutate the given Workspace in memory. No I/O.
"""

import re
import unicodedata

from pydantic import BaseModel, ValidationError

from . import models as M

TYPES: dict[str, type[BaseModel]] = {
    "groups": M.Group,
    "projects": M.Project,
    "milestones": M.Milestone,
    "references": M.Reference,
    "kinds": M.Kind,
    "states": M.State,
    "reftypes": M.RefType,
    "markers": M.Marker,
}

LABEL = {
    "groups": "Group",
    "projects": "Project",
    "milestones": "Milestone",
    "references": "Reference",
    "kinds": "Kind",
    "states": "State",
    "reftypes": "Reference type",
    "markers": "Marker",
}

SLUG_FALLBACK = {
    "groups": "group",
    "projects": "project",
    "milestones": "milestone",
    "references": "reference",
    "kinds": "kind",
    "states": "state",
    "reftypes": "reftype",
    "markers": "marker",
}

COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class Invalid(Exception):
    """The change would leave the workspace invalid (HTTP 422)."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class NotFound(Exception):
    """The addressed entity does not exist (HTTP 404)."""


class Blocked(Exception):
    """A delete is blocked (HTTP 409)."""

    def __init__(self, blockers: list[dict]):
        super().__init__(f"{len(blockers)} blocker(s)")
        self.blockers = blockers


def pydantic_messages(e: ValidationError, skip=("body",)) -> list[str]:
    out = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"] if x not in skip)
        out.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return out


def by_id(ws: M.Workspace, t: str) -> dict:
    return {e.id: e for e in getattr(ws, t)}


# ---------------------------------------------------------------- derived


def ordered(ws: M.Workspace) -> dict[str, list[M.Milestone]]:
    """Milestones per project, by date then creation (= list) order."""
    out: dict[str, list] = {p.id: [] for p in ws.projects}
    for i, m in enumerate(ws.milestones):
        out.setdefault(m.project, []).append((m.date, i, m))
    return {
        pid: [m for _, _, m in sorted(lst, key=lambda x: (x[0], x[1]))]
        for pid, lst in out.items()
    }


def parents(ws: M.Workspace, order=None) -> dict[str, list[str]]:
    order = order if order is not None else ordered(ws)
    projects = by_id(ws, "projects")
    par: dict[str, list[str]] = {}
    for pid, ms in order.items():
        for i, m in enumerate(ms):
            p: list[str] = []
            if i > 0:
                p.append(ms[i - 1].id)
            else:
                proj = projects.get(pid)
                if proj is not None and proj.from_:
                    p.append(proj.from_)
            p.extend(m.merges)
            par[m.id] = p
    return par


def head(ms: list[M.Milestone]) -> M.Milestone | None:
    real = [m for m in ms if not m.planned]
    return real[-1] if real else None


def derive(ws: M.Workspace) -> M.Derived:
    order = ordered(ws)
    merge_sources = {s for m in ws.milestones for s in m.merges}
    projects = {}
    for p in ws.projects:
        ms = order.get(p.id, [])
        h = head(ms)
        projects[p.id] = M.ProjectDerived(
            milestones=[m.id for m in ms],
            head=h.id if h else None,
            current_state=h.state if h else None,
            merged=bool(h and h.id in merge_sources),
        )
    return M.Derived(projects=projects, parents=parents(ws, order))


# ---------------------------------------------------------------- validation


def find_cycle(ws: M.Workspace) -> list[str]:
    """Milestones on a cycle of in-project order, forks, merges and directed
    references (edge from ancestor to descendant). Empty if acyclic."""
    nodes = {m.id for m in ws.milestones}
    out: dict[str, set[str]] = {n: set() for n in nodes}
    inc: dict[str, set[str]] = {n: set() for n in nodes}

    def add(a, b):
        if a in nodes and b in nodes:
            out[a].add(b)
            inc[b].add(a)

    for child, ps in parents(ws).items():
        for p in ps:
            add(p, child)
    reftypes = by_id(ws, "reftypes")
    for r in ws.references:
        rt = reftypes.get(r.type)
        if rt is not None and rt.directed:
            add(r.to, r.from_)  # `from` builds on `to`

    # Peel off sources, then sinks; whatever is left lies on a cycle.
    alive = set(nodes)
    changed = True
    while changed:
        changed = False
        for n in list(alive):
            if not (inc[n] & alive) or not (out[n] & alive):
                alive.discard(n)
                changed = True
    return sorted(alive)


def validate(ws: M.Workspace) -> list[str]:
    errs: list[str] = []
    idx: dict[str, dict] = {}
    for t in TYPES:
        seen: dict = {}
        for e in getattr(ws, t):
            if e.id in seen:
                errs.append(f"{LABEL[t]} id '{e.id}' is used more than once.")
            seen[e.id] = e
        idx[t] = seen

    def color(owner: str, c):
        if c is not None and not COLOR_RE.match(c):
            errs.append(f"{owner}: colour '{c}' is not of the form #RRGGBB.")

    for t in TYPES:
        for e in getattr(ws, t):
            owner = f"{LABEL[t]} '{e.id}'"
            if t == "groups" and e.color is None:
                errs.append(f"{owner} has no colour.")
            color(owner, e.color)
    color("Settings fork_color", ws.settings.fork_color)
    color("Settings merge_color", ws.settings.merge_color)

    def ref(owner: str, field: str, t: str, value) -> bool:
        if value not in idx[t]:
            errs.append(f"{owner}: {field} '{value}' is not an existing {LABEL[t].lower()}.")
            return False
        return True

    order = ordered(ws)
    ms_by_id = idx["milestones"]

    for p in ws.projects:
        owner = f"Project '{p.id}'"
        ref(owner, "group", "groups", p.group)
        mine = order.get(p.id, [])
        if not mine:
            errs.append(f"{owner} has no milestones; every project needs at least one.")
        if p.from_ is not None and ref(owner, "from", "milestones", p.from_):
            origin = ms_by_id[p.from_]
            if origin.project == p.id:
                errs.append(f"{owner}: cannot fork from its own milestone '{p.from_}'.")
            elif mine and origin.date > mine[0].date:
                errs.append(
                    f"{owner}: fork origin '{p.from_}' ({origin.date}) is dated after "
                    f"the project's first milestone '{mine[0].id}' ({mine[0].date})."
                )

    for m in ws.milestones:
        owner = f"Milestone '{m.id}'"
        ref(owner, "project", "projects", m.project)
        ref(owner, "kind", "kinds", m.kind)
        if m.state is None:
            errs.append(f"{owner} has no state.")
        else:
            ref(owner, "state", "states", m.state)
        for mk in m.markers:
            ref(owner, "markers", "markers", mk)
        for s in m.merges:
            if not ref(owner, "merges", "milestones", s):
                continue
            src = ms_by_id[s]
            if src.project == m.project:
                errs.append(f"{owner}: cannot merge '{s}' from its own project.")
            elif src.date > m.date:
                errs.append(
                    f"{owner}: merge source '{s}' ({src.date}) is dated after "
                    f"the merging milestone ({m.date})."
                )

    for r in ws.references:
        owner = f"Reference '{r.id}'"
        ref(owner, "type", "reftypes", r.type)
        ref(owner, "from", "milestones", r.from_)
        ref(owner, "to", "milestones", r.to)
        if r.from_ == r.to:
            errs.append(f"{owner}: from and to must differ.")

    for k in ws.kinds:
        if k.default_state is not None:
            ref(f"Kind '{k.id}'", "default_state", "states", k.default_state)

    cycle = find_cycle(ws)
    if cycle:
        errs.append("History has a cycle through milestones: " + ", ".join(cycle) + ".")
    return errs


# ---------------------------------------------------------------- ids


def slugify(text: str, fallback: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or fallback


def unique(base: str, existing) -> str:
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


# ---------------------------------------------------------------- create / patch


def default_state(ws: M.Workspace, kind: str, project: str, date) -> str | None:
    """Kind's default state, else the state of the milestone that will precede
    the new one (the fork origin for a project's first milestone)."""
    k = by_id(ws, "kinds").get(kind)
    if k is not None and k.default_state:
        return k.default_state
    prev = [m for m in ordered(ws).get(project, []) if m.date <= date]
    if prev:
        return prev[-1].state
    p = by_id(ws, "projects").get(project)
    if p is not None and p.from_:
        origin = by_id(ws, "milestones").get(p.from_)
        if origin is not None:
            return origin.state
    return None


def _add_milestone(ws: M.Workspace, fields: dict) -> M.Milestone:
    pid = fields["project"]
    mid = unique(f"{pid}.{slugify(fields['title'], 'milestone')}", by_id(ws, "milestones"))
    if fields.get("state") is None:
        fields["state"] = default_state(ws, fields["kind"], pid, fields["date"])
    m = M.Milestone.model_validate({"id": mid, **fields})
    ws.milestones.append(m)
    return m


def create(ws: M.Workspace, t: str, data: BaseModel):
    if t == "projects":
        fields = data.model_dump(by_alias=True, exclude={"first_milestone"})
        pid = unique(slugify(fields["title"], "project"), by_id(ws, "projects"))
        p = M.Project.model_validate({"id": pid, **fields})
        ws.projects.append(p)
        _add_milestone(ws, {**data.first_milestone.model_dump(by_alias=True), "project": pid})
        return p
    fields = data.model_dump(by_alias=True)
    if t == "milestones":
        return _add_milestone(ws, fields)
    source = fields["type"] if t == "references" else fields["name"]
    eid = unique(slugify(source, SLUG_FALLBACK[t]), by_id(ws, t))
    e = TYPES[t].model_validate({"id": eid, **fields})
    getattr(ws, t).append(e)
    return e


def patch(ws: M.Workspace, t: str, eid: str, data: dict):
    lst = getattr(ws, t)
    i = next((i for i, e in enumerate(lst) if e.id == eid), None)
    if i is None:
        raise NotFound(f"{LABEL[t]} '{eid}' does not exist.")
    data = dict(data)
    position = data.pop("position", None)
    merged = {**lst[i].model_dump(by_alias=True), **data, "id": eid}
    try:
        new = TYPES[t].model_validate(merged)
    except ValidationError as e:
        raise Invalid(pydantic_messages(e)) from None
    old = lst[i]
    lst[i] = new
    if position is not None:
        lst.insert(max(0, min(position, len(lst) - 1)), lst.pop(i))
    if t == "projects" and new.group != old.group:
        # Its lane subtree (forks drawn under it) moves along to the new group.
        moving = lane_subtree(ws, eid, old.group)
        for p in ws.projects:
            if p.id in moving:
                p.group = new.group
    return new


def lane_subtree(ws: M.Workspace, pid: str, group: str) -> set[str]:
    """Projects drawn under `pid` in `group`: its forks in that group, their
    forks in that group, and so on (forks into other groups start their own tree)."""
    ms_project = {m.id: m.project for m in ws.milestones}
    out: set[str] = set()
    frontier = [pid]
    while frontier:
        parent = frontier.pop()
        for p in ws.projects:
            if p.id not in out and p.group == group and p.from_ and ms_project.get(p.from_) == parent:
                out.add(p.id)
                frontier.append(p.id)
    return out


# ---------------------------------------------------------------- delete


def delete_plan(ws: M.Workspace, t: str, eid: str) -> tuple[list[dict], list[dict]]:
    """What deleting (t, eid) removes, and what blocks it."""
    if eid not in by_id(ws, t):
        raise NotFound(f"{LABEL[t]} '{eid}' does not exist.")
    removes = [{"type": t, "id": eid}]
    blockers: list[dict] = []

    def block(bt, bid, reason):
        blockers.append({"type": bt, "id": bid, "reason": reason})

    def refs_touching(mids):
        return [
            {"type": "references", "id": r.id}
            for r in ws.references
            if r.from_ in mids or r.to in mids
        ]

    if t == "groups":
        for p in ws.projects:
            if p.group == eid:
                block("projects", p.id, f"belongs to group '{eid}'")
    elif t == "projects":
        mine = ordered(ws).get(eid, [])
        mids = {m.id for m in mine}
        removes += [{"type": "milestones", "id": m.id} for m in mine]
        removes += refs_touching(mids)
        for p in ws.projects:
            if p.id != eid and p.from_ in mids:
                block("projects", p.id, f"forks from '{p.from_}'")
        for m in ws.milestones:
            if m.project != eid:
                for s in m.merges:
                    if s in mids:
                        block("milestones", m.id, f"merges '{s}'")
    elif t == "milestones":
        ms = by_id(ws, "milestones")
        removes += refs_touching({eid})
        for p in ws.projects:
            if p.from_ == eid:
                block("projects", p.id, "forks from this milestone")
        for m in ws.milestones:
            if eid in m.merges:
                block("milestones", m.id, "merges this milestone")
        pid = ms[eid].project
        if sum(1 for m in ws.milestones if m.project == pid) == 1:
            block("projects", pid, "this is the project's only milestone")
    elif t == "kinds":
        for m in ws.milestones:
            if m.kind == eid:
                block("milestones", m.id, "has this kind")
    elif t == "states":
        for m in ws.milestones:
            if m.state == eid:
                block("milestones", m.id, "is in this state")
        for k in ws.kinds:
            if k.default_state == eid:
                block("kinds", k.id, "uses this state as its default")
    elif t == "reftypes":
        for r in ws.references:
            if r.type == eid:
                block("references", r.id, "has this type")
    elif t == "markers":
        for m in ws.milestones:
            if eid in m.markers:
                block("milestones", m.id, "has this marker")
    return removes, blockers


def apply_delete(ws: M.Workspace, removes: list[dict]) -> None:
    for t in TYPES:
        ids = {r["id"] for r in removes if r["type"] == t}
        if ids:
            setattr(ws, t, [e for e in getattr(ws, t) if e.id not in ids])


def delete(ws: M.Workspace, t: str, eid: str) -> None:
    removes, blockers = delete_plan(ws, t, eid)
    if blockers:
        raise Blocked(blockers)
    apply_delete(ws, removes)
