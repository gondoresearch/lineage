def ids(ws, t):
    return {e["id"] for e in ws[t]}


def workspace(client):
    return client.get("/api/workspace").json()


def refs(items):
    return {(x["type"], x["id"]) for x in items}


# ------------------------------------------------------------------ groups


def test_group_blocked_while_it_has_projects(client):
    r = client.delete("/api/groups/teaching")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {("projects", "statistics-notes"), ("projects", "graph-course")}
    assert "teaching" in ids(workspace(client), "groups")


def test_empty_group_deleted(client):
    client.post("/api/groups", json={"name": "Spare", "color": "#000000"})
    assert client.delete("/api/groups/spare").status_code == 204
    assert "spare" not in ids(workspace(client), "groups")


# ------------------------------------------------------------------ projects


def test_project_delete_cascades(client, example_dir):
    # graph-course: 2 milestones, references builds-on-2 and companion
    dry = client.delete("/api/projects/graph-course", params={"dry_run": True})
    assert dry.status_code == 200
    assert refs(dry.json()["removes"]) == {
        ("projects", "graph-course"),
        ("milestones", "graph-course.draft"),
        ("milestones", "graph-course.preprint"),
        ("references", "builds-on-2"),
        ("references", "companion"),
    }
    assert dry.json()["blockers"] == []
    assert client.delete("/api/projects/graph-course").status_code == 204
    ws = workspace(client)
    assert "graph-course" not in ids(ws, "projects")
    assert not any(m["project"] == "graph-course" for m in ws["milestones"])
    # the other references of the example data (incl. the lineage-development domain) are untouched
    assert ids(ws, "references") == {"builds-on", "builds-on-3", "builds-on-4", "companion-2"}


def test_project_delete_removes_description_files(client, example_dir):
    f = example_dir / "descriptions" / "projects" / "bayesian-rainfall.md"
    # bayesian-rainfall is merged into extreme-rainfall: blocked
    assert client.delete("/api/projects/bayesian-rainfall").status_code == 409
    client.patch("/api/milestones/extreme-rainfall.submitted", json={"merges": []})
    assert client.delete("/api/projects/bayesian-rainfall").status_code == 204
    assert not f.exists()


def test_project_blocked_by_fork(client):
    r = client.delete("/api/projects/spectral-filters")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {
        ("projects", "spectral-filters-journal"),
        ("projects", "station-graphs"),
    }


def test_project_blocked_by_merge(client):
    r = client.delete("/api/projects/bayesian-rainfall", params={"dry_run": True})
    assert r.status_code == 200
    assert r.json()["blockers"] == [
        {"type": "milestones", "id": "extreme-rainfall.submitted", "reason": "merges 'bayesian-rainfall.v2'"}
    ]


# ------------------------------------------------------------------ milestones


def test_milestone_delete_cascades_references(client, example_dir):
    r = client.delete("/api/milestones/spectral-filters.published", params={"dry_run": True})
    assert refs(r.json()["removes"]) == {
        ("milestones", "spectral-filters.published"),
        ("references", "builds-on-2"),
    }
    assert client.delete("/api/milestones/spectral-filters.published").status_code == 204
    assert "builds-on-2" not in ids(workspace(client), "references")


def test_milestone_blocked_as_fork_origin(client):
    r = client.delete("/api/milestones/spectral-filters.accepted")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {("projects", "spectral-filters-journal")}


def test_milestone_blocked_as_merge_source(client):
    r = client.delete("/api/milestones/bayesian-rainfall.v2")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {("milestones", "extreme-rainfall.submitted")}


def test_only_milestone_blocked(client):
    client.post("/api/projects", json={"title": "Solo", "group": "teaching",
                                       "first_milestone": {"title": "v1", "date": "2026-01-01", "kind": "draft"}})
    r = client.delete("/api/milestones/solo.v1")
    assert r.status_code == 409
    assert r.json()["blockers"][0]["reason"] == "this is the project's only milestone"


def test_milestone_description_file_deleted(client, example_dir):
    f = example_dir / "descriptions" / "milestones" / "spectral-filters.rejected.md"
    assert f.exists()
    assert client.delete("/api/milestones/spectral-filters.rejected").status_code == 204
    assert not f.exists()


# ------------------------------------------------------------------ references


def test_reference_delete(client, example_dir):
    assert client.delete("/api/references/builds-on").status_code == 204
    assert "builds-on" not in ids(workspace(client), "references")
    assert not (example_dir / "descriptions" / "references" / "builds-on.md").exists()


# ------------------------------------------------------------------ vocabulary


def test_kind_blocked_while_in_use(client):
    r = client.delete("/api/kinds/rejected")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {("milestones", "spectral-filters.rejected")}


def test_state_blocked_by_milestones_and_kinds(client):
    r = client.delete("/api/states/revising")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {("milestones", "spectral-filters.rejected"), ("kinds", "rejected")}


def test_reftype_blocked_while_in_use(client):
    r = client.delete("/api/reftypes/companion")
    assert r.status_code == 409
    assert refs(r.json()["blockers"]) == {("references", "companion"), ("references", "companion-2")}


def test_unused_vocabulary_deleted(client):
    for t, body in [
        ("kinds", {"name": "talk", "shape": "diamond"}),
        ("states", {"name": "idle", "line": "dotted", "waiting_on": "nobody"}),
        ("reftypes", {"name": "cites", "directed": True, "line": "dashed"}),
    ]:
        eid = client.post(f"/api/{t}", json=body).json()["id"]
        assert client.delete(f"/api/{t}/{eid}").status_code == 204
        assert eid not in ids(workspace(client), t)


# ------------------------------------------------------------------ dry run, 404


def test_dry_run_changes_nothing(client, example_dir):
    before = (example_dir / "workspace.yaml").read_text()
    r = client.delete("/api/projects/graph-course", params={"dry_run": True})
    assert r.status_code == 200
    assert (example_dir / "workspace.yaml").read_text() == before
    assert not (example_dir / ".history").exists()


def test_dry_run_blocked_lists_blockers(client):
    r = client.delete("/api/groups/teaching", params={"dry_run": True})
    assert r.status_code == 200
    assert r.json()["removes"] == [{"type": "groups", "id": "teaching"}]
    assert len(r.json()["blockers"]) == 2


def test_delete_unknown_is_404(client):
    r = client.delete("/api/kinds/nope")
    assert r.status_code == 404 and r.json()["errors"]
