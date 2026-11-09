import datetime as dt

from backend import graph
from backend import models as M


def test_order_by_date_then_creation(example_ws):
    ws = example_ws
    # Two new milestones on the same date: list (creation) order breaks the tie.
    ws.milestones.append(M.Milestone(id="graph-sampling.b", project="graph-sampling", title="b",
                                     at=dt.datetime(2026, 5, 1), kind="draft", state="drafting"))
    ws.milestones.append(M.Milestone(id="graph-sampling.a", project="graph-sampling", title="a",
                                     at=dt.datetime(2026, 5, 1), kind="draft", state="drafting"))
    ids = [m.id for m in graph.ordered(ws)["graph-sampling"]]
    assert ids == ["graph-sampling.draft", "graph-sampling.b", "graph-sampling.a", "graph-sampling.submit"]


def test_parents_in_project(example_ws):
    par = graph.parents(example_ws)
    assert par["spectral-filters.draft"] == []
    assert par["spectral-filters.preprint"] == ["spectral-filters.draft"]


def test_fork_parent_is_origin(example_ws):
    par = graph.parents(example_ws)
    assert par["spectral-filters-journal.draft"] == ["spectral-filters.accepted"]
    assert par["spectral-filters-tutorial.draft"] == ["spectral-filters-journal.draft"]
    assert par["station-graphs.draft"] == ["spectral-filters.preprint"]


def test_merge_parents(example_ws):
    par = graph.parents(example_ws)
    assert par["extreme-rainfall.submitted"] == ["extreme-rainfall.preprint", "bayesian-rainfall.v2"]


def test_head_skips_planned(example_ws):
    d = graph.derive(example_ws).projects
    assert d["spectral-filters-journal"].head == "spectral-filters-journal.revision"
    assert d["graph-sampling"].head == "graph-sampling.draft"
    assert d["spectral-filters"].head == "spectral-filters.published"


def test_head_none_when_all_planned(example_ws):
    for m in example_ws.milestones:
        if m.project == "graph-course":
            m.planned = True
    d = graph.derive(example_ws).projects["graph-course"]
    assert d.head is None and d.current_state is None and not d.merged


def test_current_state(example_ws):
    d = graph.derive(example_ws).projects
    assert d["spectral-filters-tutorial"].current_state == "paused"
    assert d["station-graphs"].current_state == "under-review"


def test_merged(example_ws):
    d = graph.derive(example_ws).projects
    assert d["bayesian-rainfall"].merged
    assert not d["extreme-rainfall"].merged
    assert not d["spectral-filters"].merged  # forked from, not merged


def test_merge_of_non_head_is_not_merged(example_ws):
    example_ws.milestones.append(M.Milestone(id="bayesian-rainfall.v3", project="bayesian-rainfall", title="v3",
                                             at=dt.datetime(2026, 1, 1), kind="draft", state="drafting"))
    assert not graph.derive(example_ws).projects["bayesian-rainfall"].merged


def test_derived_milestone_order_listed(example_ws):
    d = graph.derive(example_ws).projects["spectral-filters"]
    assert d.milestones[0] == "spectral-filters.draft"
    assert d.milestones[-1] == "spectral-filters.published"


def test_default_state_rules(example_ws):
    ws = example_ws
    # kind default
    assert graph.default_state(ws, "submitted", "graph-course", dt.datetime(2027, 1, 1)) == "under-review"
    # previous milestone's state (preprint has no default)
    assert graph.default_state(ws, "preprint", "graph-course", dt.datetime(2026, 6, 1)) == "drafting"
    # fork origin's state for a first milestone
    ws.projects.append(M.Project(id="f", title="f", group="teaching", **{"from": "graph-course.preprint"}))
    assert graph.default_state(ws, "preprint", "f", dt.datetime(2026, 10, 1)) == "with-co-authors"
    # nothing to inherit
    ws.projects.append(M.Project(id="g", title="g", group="teaching"))
    assert graph.default_state(ws, "preprint", "g", dt.datetime(2026, 10, 1)) is None


def test_slugify():
    assert graph.slugify("Spectral Filters: v2!", "x") == "spectral-filters-v2"
    assert graph.slugify("Résumé", "x") == "resume"
    assert graph.slugify("—", "milestone") == "milestone"
    assert graph.unique("a", {"a", "a-2"}) == "a-3"
