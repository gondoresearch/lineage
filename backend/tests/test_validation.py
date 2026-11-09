import datetime as dt

import pytest

from backend import graph
from backend import models as M


def ms(ws, mid):
    return next(m for m in ws.milestones if m.id == mid)


def proj(ws, pid):
    return next(p for p in ws.projects if p.id == pid)


def errors_with(ws, needle):
    errs = graph.validate(ws)
    assert any(needle in e for e in errs), errs
    return errs


def test_example_is_valid(example_ws):
    assert graph.validate(example_ws) == []


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda ws: setattr(proj(ws, "graph-sampling"), "group", "nope"), "group 'nope'"),
        (lambda ws: setattr(ms(ws, "graph-sampling.draft"), "project", "nope"), "project 'nope'"),
        (lambda ws: setattr(ms(ws, "graph-sampling.draft"), "kind", "nope"), "kind 'nope'"),
        (lambda ws: setattr(ms(ws, "graph-sampling.draft"), "state", "nope"), "state 'nope'"),
        (lambda ws: setattr(ms(ws, "graph-sampling.draft"), "merges", ["nope"]), "merges 'nope'"),
        (lambda ws: setattr(proj(ws, "graph-sampling"), "from_", "nope"), "from 'nope'"),
        (lambda ws: setattr(ws.references[0], "type", "nope"), "type 'nope'"),
        (lambda ws: setattr(ws.references[0], "from_", "nope"), "from 'nope'"),
        (lambda ws: setattr(ws.references[0], "to", "nope"), "to 'nope'"),
        (lambda ws: setattr(ws.kinds[0], "default_state", "nope"), "default_state 'nope'"),
    ],
)
def test_unresolved_references(example_ws, mutate, needle):
    mutate(example_ws)
    errors_with(example_ws, needle)


def test_missing_state(example_ws):
    ms(example_ws, "graph-sampling.draft").state = None
    errors_with(example_ws, "has no state")


def test_fork_from_own_project(example_ws):
    proj(example_ws, "graph-sampling").from_ = "graph-sampling.submit"
    errors_with(example_ws, "own milestone")


def test_fork_origin_after_first_milestone(example_ws):
    proj(example_ws, "graph-sampling").from_ = "spectral-filters-journal.revision"  # 2026-08-20 > 2026-04-10
    errors_with(example_ws, "dated after the project's first milestone")


def test_fork_origin_same_day_ok(example_ws):
    proj(example_ws, "graph-sampling").from_ = "spectral-filters.published"
    ms(example_ws, "graph-sampling.draft").at = dt.datetime(2026, 2, 10)
    assert graph.validate(example_ws) == []


def test_merge_from_own_project(example_ws):
    ms(example_ws, "graph-sampling.submit").merges = ["graph-sampling.draft"]
    errors_with(example_ws, "from its own project")


def test_merge_source_after_merging(example_ws):
    ms(example_ws, "graph-sampling.draft").merges = ["graph-course.preprint"]  # 2026-09-15 > 2026-04-10
    errors_with(example_ws, "dated after the merging milestone")


def test_reference_from_equals_to(example_ws):
    example_ws.references[0].to = example_ws.references[0].from_
    errors_with(example_ws, "must differ")


@pytest.mark.parametrize("bad", ["red", "#12345", "#1234567", "#GGGGGG", "112233"])
def test_bad_colours(example_ws, bad):
    proj(example_ws, "graph-sampling").color = bad
    errors_with(example_ws, "#RRGGBB")


def test_bad_settings_colour(example_ws):
    example_ws.settings.fork_color = "blue"
    errors_with(example_ws, "fork_color")


def test_group_needs_colour(example_ws):
    example_ws.groups[0].color = None
    errors_with(example_ws, "has no colour")


def test_null_colours_inherit(example_ws):
    example_ws.kinds[0].color = None
    proj(example_ws, "spectral-filters-tutorial").color = None
    example_ws.settings.fork_color = None
    assert graph.validate(example_ws) == []


def test_project_needs_a_milestone(example_ws):
    example_ws.projects.append(M.Project(id="empty", title="Empty", group="teaching"))
    errors_with(example_ws, "has no milestones")


def test_duplicate_ids(example_ws):
    example_ws.groups.append(M.Group(id="teaching", name="Again", color="#000000"))
    errors_with(example_ws, "used more than once")


def test_cycle_through_directed_reference(example_ws):
    # statistics-notes.draft builds on its own later milestone -> cycle
    example_ws.references.append(M.Reference(id="x", type="builds-on", **{"from": "statistics-notes.draft"},
                                             to="statistics-notes.published"))
    errors_with(example_ws, "cycle")


def test_cycle_across_projects(example_ws):
    # graph-course.draft builds on spectral-filters.published already;
    # spectral-filters.published building on graph-course.preprint closes a loop.
    example_ws.references.append(M.Reference(id="x", type="builds-on", **{"from": "spectral-filters.published"},
                                             to="graph-course.preprint"))
    errs = errors_with(example_ws, "cycle")
    assert any("graph-course.draft" in e for e in errs)


def test_cycle_through_same_day_merges(example_ws):
    ws = example_ws
    a = ms(ws, "graph-course.draft")
    b = ms(ws, "graph-sampling.draft")
    b.at = a.at  # same day
    a.merges = ["graph-sampling.draft"]
    b.merges = ["graph-course.draft"]
    errors_with(ws, "cycle")


def test_undirected_reference_no_cycle(example_ws):
    example_ws.references.append(M.Reference(id="x", type="companion", **{"from": "statistics-notes.draft"},
                                             to="statistics-notes.published"))
    assert graph.validate(example_ws) == []


def test_planned_in_past_allowed(example_ws):
    m = ms(example_ws, "graph-sampling.submit")
    assert m.planned and m.at < dt.datetime(2026, 11, 6)
    assert graph.validate(example_ws) == []


def test_api_returns_422_with_messages(client):
    r = client.patch("/api/projects/graph-sampling", json={"group": "nope"})
    assert r.status_code == 422
    assert any("group 'nope'" in e for e in r.json()["errors"])


def test_api_request_validation_shape(client):
    r = client.post("/api/states", json={"name": "x", "line": "wavy", "waiting_on": "me"})
    assert r.status_code == 422
    body = r.json()
    assert list(body) == ["errors"] and body["errors"][0].startswith("line:")


def test_api_rejects_bad_colour(client):
    r = client.patch("/api/kinds/draft", json={"color": "red"})
    assert r.status_code == 422


def test_invalid_write_changes_nothing(client, example_dir):
    before = (example_dir / "workspace.yaml").read_text()
    client.patch("/api/projects/graph-sampling", json={"group": "nope"})
    assert (example_dir / "workspace.yaml").read_text() == before
    assert not (example_dir / ".history").exists()
