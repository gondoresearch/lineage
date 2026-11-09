import yaml

from backend import graph
from backend import models as M
from backend.store import Store


# ------------------------------------------------------------------ domains


def test_domain_crud_and_group_assignment(client, example_dir):
    r = client.post("/api/domains", json={"name": "Outreach", "color": "#334455", "description": "Talks."})
    assert r.status_code == 201 and r.json()["id"] == "outreach"
    assert (example_dir / "descriptions" / "domains" / "outreach.md").read_text() == "Talks."
    assert client.patch("/api/groups/teaching", json={"domain": "outreach"}).json()["domain"] == "outreach"
    r = client.post("/api/groups", json={"name": "Talks", "color": "#000000", "domain": "outreach"})
    assert r.json()["domain"] == "outreach"
    # groups without a domain stay valid
    client.patch("/api/groups/teaching", json={"domain": None})
    groups = {g["id"]: g["domain"] for g in client.get("/api/workspace").json()["groups"]}
    assert groups["teaching"] is None and groups["graph-learning"] == "research"


def test_group_domain_must_exist(client):
    r = client.patch("/api/groups/teaching", json={"domain": "nope"})
    assert r.status_code == 422 and any("domain 'nope'" in e for e in r.json()["errors"])


def test_domain_delete_blocked_while_it_has_groups(client):
    client.post("/api/domains", json={"name": "Outreach"})
    client.patch("/api/groups/teaching", json={"domain": "outreach"})
    r = client.delete("/api/domains/outreach")
    assert r.status_code == 409
    assert r.json()["blockers"] == [{"type": "groups", "id": "teaching", "reason": "belongs to domain 'outreach'"}]
    client.patch("/api/groups/teaching", json={"domain": None})
    assert client.delete("/api/domains/outreach").status_code == 204


def test_domain_order(client):
    for n in ("A", "B", "C"):
        client.post("/api/domains", json={"name": n})
    client.patch("/api/domains/c", json={"position": 0})
    assert [d["id"] for d in client.get("/api/workspace").json()["domains"]] == ["c", "research", "a", "b"]


# ------------------------------------------------------------------ closing kinds


def test_closing_milestone_needs_no_state(client):
    r = client.post("/api/milestones", json={"project": "graph-course", "title": "end", "at": "2026-10-30", "kind": "closed"})
    assert r.status_code == 201 and r.json()["state"] is None
    d = client.get("/api/workspace").json()["derived"]["projects"]["graph-course"]
    assert d["head"] == "graph-course.end" and d["closed"] is True and d["current_state"] is None


def test_other_kinds_still_need_a_state(example_ws):
    m = next(m for m in example_ws.milestones if m.id == "graph-sampling.draft")
    m.state = None
    assert any("has no state" in e for e in graph.validate(example_ws))
    m.kind = "closed"
    assert graph.validate(example_ws) == []


def test_closing_kind_does_not_inherit_a_state(example_ws):
    assert graph.default_state(example_ws, "closed", "graph-course", __import__("datetime").datetime(2026, 12, 1)) is None


# ------------------------------------------------------------------ migration of the old 'closed' state


def test_old_closed_state_is_converted_on_load(tmp_path):
    d = tmp_path / "old"
    old = graph.migrate  # make sure the example data still exercises the migration path
    ws = M.Workspace(
        groups=[M.Group(id="g", name="g", color="#000000")],
        projects=[M.Project(id="p", title="p", group="g")],
        kinds=[M.Kind(id="draft", name="draft", shape="open-circle")],
        states=[M.State(id="drafting", name="drafting", line="solid", waiting_on="me"),
                M.State(id="closed", name="closed", line="dotted", waiting_on="nobody")],
        milestones=[M.Milestone(id="p.1", project="p", title="1", at="2025-01-01", kind="draft", state="drafting"),
                    M.Milestone(id="p.2", project="p", title="2", at="2025-02-01", kind="draft", state="closed")],
    )
    d.mkdir()
    (d / "workspace.yaml").write_text(yaml.safe_dump(ws.model_dump(by_alias=True, mode="json"), sort_keys=False))
    loaded = Store(d).read()
    assert [s.id for s in loaded.states] == ["drafting"]
    closed = next(k for k in loaded.kinds if k.id == "closed")
    assert closed.closes and closed.shape == "filled-square"
    m2 = next(m for m in loaded.milestones if m.id == "p.2")
    assert (m2.kind, m2.state) == ("closed", None)
    assert graph.derive(loaded).projects["p"].closed is True
    assert old is graph.migrate


def test_example_data_has_no_closed_state(client):
    ws = client.get("/api/workspace").json()
    assert "closed" not in {s["id"] for s in ws["states"]}
    assert next(m for m in ws["milestones"] if m["id"] == "bayesian-rainfall.v2")["kind"] == "closed"
