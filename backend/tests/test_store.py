import os

import yaml

from backend import store as S


def bump_mtime(path):
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


# ------------------------------------------------------------------ seed


def test_seed_on_first_run(empty_client, tmp_path):
    ws = empty_client.get("/api/workspace").json()
    assert {k["id"] for k in ws["kinds"]} == {"draft", "preprint", "submitted", "revision", "accepted", "published", "rejected", "closed"}
    assert {s["id"] for s in ws["states"]} == {"drafting", "revising", "with-co-authors", "under-review", "paused",
                                               "accepted", "published"}  # 'closed' is a kind now
    assert {r["id"]: r["directed"] for r in ws["reftypes"]} == {"builds-on": True, "companion": False}
    assert ws["groups"] == [] and ws["projects"] == []
    kinds = {k["id"]: k for k in ws["kinds"]}
    assert kinds["rejected"]["default_state"] == "revising" and kinds["preprint"]["default_state"] is None
    assert {k: v["shape"] for k, v in kinds.items()} == {
        "draft": "open-circle", "preprint": "star", "submitted": "triangle", "revision": "diamond",
        "accepted": "filled-circle", "published": "filled-star", "rejected": "cross", "closed": "filled-square",
    }
    assert [k["id"] for k in ws["kinds"] if k["closes"]] == ["closed"]
    assert all(e["color"] is None for t in ("kinds", "states", "reftypes") for e in ws[t])
    assert (tmp_path / "fresh" / "workspace.yaml").exists()


def test_seed_not_rewritten(example_dir):
    before = (example_dir / "workspace.yaml").read_text()
    S.Store(example_dir)
    assert (example_dir / "workspace.yaml").read_text() == before


# ------------------------------------------------------------------ ids


def test_ids_are_slugs_with_suffix(empty_client):
    c = empty_client
    assert c.post("/api/groups", json={"name": "My Group", "color": "#000000"}).json()["id"] == "my-group"
    assert c.post("/api/groups", json={"name": "My group!", "color": "#000000"}).json()["id"] == "my-group-2"
    p = c.post("/api/projects", json={"title": "Paper", "group": "my-group",
                                      "first_milestone": {"title": "v1", "date": "2026-01-01", "kind": "draft"}})
    assert p.status_code == 201 and p.json()["id"] == "paper"
    m = c.post("/api/milestones", json={"project": "paper", "title": "V1", "date": "2026-02-01", "kind": "draft"})
    assert m.json()["id"] == "paper.v1-2"
    r = c.post("/api/references", json={"type": "companion", "from": "paper.v1", "to": "paper.v1-2"})
    assert r.json()["id"] == "companion"


def test_ids_immutable_on_rename(client):
    r = client.patch("/api/projects/graph-sampling", json={"title": "Renamed"})
    assert r.json()["id"] == "graph-sampling" and r.json()["title"] == "Renamed"
    r = client.patch("/api/milestones/graph-sampling.draft", json={"title": "first", "id": "x"})
    assert r.status_code == 422  # id is not a patchable field
    r = client.patch("/api/milestones/graph-sampling.draft", json={"title": "first"})
    assert r.json()["id"] == "graph-sampling.draft"


def test_milestone_project_not_patchable(client):
    r = client.patch("/api/milestones/graph-sampling.draft", json={"project": "graph-course"})
    assert r.status_code == 422


def test_created_milestone_default_states(client):
    m = client.post("/api/milestones", json={"project": "graph-course", "title": "sub", "date": "2026-10-01",
                                             "kind": "submitted"}).json()
    assert m["state"] == "under-review"
    m = client.post("/api/milestones", json={"project": "graph-course", "title": "pp", "date": "2026-10-02",
                                             "kind": "preprint"}).json()
    assert m["state"] == "under-review"  # previous milestone's state
    p = client.post("/api/projects", json={"title": "Fork", "group": "teaching", "from": "graph-course.preprint",
                                           "first_milestone": {"title": "v1", "date": "2026-09-20", "kind": "preprint"}})
    assert p.status_code == 201
    ws = client.get("/api/workspace").json()
    first = next(m for m in ws["milestones"] if m["id"] == "fork.v1")
    assert first["state"] == "with-co-authors"


def test_milestone_without_inheritable_state_rejected(client):
    r = client.post("/api/projects", json={"title": "X", "group": "teaching",
                                           "first_milestone": {"title": "v1", "date": "2026-01-01", "kind": "preprint"}})
    assert r.status_code == 422 and any("has no state" in e for e in r.json()["errors"])


def test_merge_is_milestone_with_merges(client):
    r = client.post("/api/milestones", json={"project": "graph-course", "title": "merge", "date": "2026-10-10",
                                             "kind": "draft", "merges": ["graph-sampling.draft"]})
    assert r.status_code == 201
    d = client.get("/api/workspace").json()["derived"]
    assert d["parents"]["graph-course.merge"] == ["graph-course.preprint", "graph-sampling.draft"]


def test_group_reorder(client):
    def order():
        return [g["id"] for g in client.get("/api/workspace").json()["groups"]]
    assert order() == ["graph-learning", "climate-statistics", "teaching"]
    client.patch("/api/groups/teaching", json={"position": 0})
    assert order() == ["teaching", "graph-learning", "climate-statistics"]
    client.patch("/api/groups/teaching", json={"position": 99})
    assert order() == ["graph-learning", "climate-statistics", "teaching"]


def test_settings_patch(client):
    r = client.patch("/api/settings", json={"fork_color": None})
    assert r.json() == {"fork_color": None, "merge_color": "#8c564b", "fork_width": 1.8, "merge_width": 1.8}
    assert client.patch("/api/settings", json={"merge_color": "nope"}).status_code == 422


# ------------------------------------------------------------------ descriptions


def test_descriptions_round_trip(client, example_dir):
    text = "Inline $x^2$ and\n\n$$\\int_0^1 f$$\n"
    client.patch("/api/groups/teaching", json={"description": text})
    f = example_dir / "descriptions" / "groups" / "teaching.md"
    assert f.read_text() == text
    assert "description" not in (example_dir / "workspace.yaml").read_text()
    assert next(g for g in client.get("/api/workspace").json()["groups"] if g["id"] == "teaching")["description"] == text
    # and back from a fresh process
    assert next(g for g in S.Store(example_dir).read().groups if g.id == "teaching").description == text


def test_empty_description_removes_file(client, example_dir):
    f = example_dir / "descriptions" / "states" / "paused.md"
    assert f.exists()
    client.patch("/api/states/paused", json={"description": ""})
    assert not f.exists()


def test_create_with_description(client, example_dir):
    client.post("/api/kinds", json={"name": "talk", "shape": "diamond", "description": "A talk."})
    assert (example_dir / "descriptions" / "kinds" / "talk.md").read_text() == "A talk."


# ------------------------------------------------------------------ snapshots, undo


def test_snapshot_per_write(client, example_dir):
    client.patch("/api/groups/teaching", json={"name": "T1"})
    client.patch("/api/groups/teaching", json={"name": "T2"})
    snaps = sorted((example_dir / ".history").iterdir())
    assert len(snaps) == 2
    assert "name: Teaching\n" in (snaps[0] / "workspace.yaml").read_text()
    assert "name: T1\n" in (snaps[1] / "workspace.yaml").read_text()
    assert (snaps[0] / "descriptions" / "projects" / "spectral-filters.md").exists()
    assert not (snaps[0] / ".history").exists()


def test_keep_last_20_snapshots(client, example_dir):
    for i in range(23):
        client.patch("/api/groups/teaching", json={"name": f"T{i}"})
    snaps = sorted((example_dir / ".history").iterdir())
    assert len(snaps) == 20
    assert "name: T2\n" in (snaps[0] / "workspace.yaml").read_text()


def test_undo_restores_including_descriptions(client, example_dir):
    f = example_dir / "descriptions" / "milestones" / "spectral-filters.rejected.md"
    text = f.read_text()
    assert client.delete("/api/milestones/spectral-filters.rejected").status_code == 204
    assert not f.exists()
    assert client.post("/api/undo").status_code == 204
    assert f.read_text() == text
    ids = {m["id"] for m in client.get("/api/workspace").json()["milestones"]}
    assert "spectral-filters.rejected" in ids
    assert not (example_dir / ".history").exists() or not list((example_dir / ".history").iterdir())


def test_undo_walks_back(client):
    client.patch("/api/groups/teaching", json={"name": "T1"})
    client.patch("/api/groups/teaching", json={"name": "T2"})
    client.post("/api/undo")
    name = lambda: next(g for g in client.get("/api/workspace").json()["groups"] if g["id"] == "teaching")["name"]  # noqa: E731
    assert name() == "T1"
    client.post("/api/undo")
    assert name() == "Teaching"
    r = client.post("/api/undo")
    assert r.status_code == 409 and r.json() == {"errors": ["Nothing to undo."]}


def test_undo_removes_created_description(client, example_dir):
    client.post("/api/kinds", json={"name": "talk", "shape": "diamond", "description": "A talk."})
    client.post("/api/undo")
    assert not (example_dir / "descriptions" / "kinds" / "talk.md").exists()


# ------------------------------------------------------------------ reload on hand edit


def test_reload_after_hand_edit(client, example_dir):
    p = example_dir / "workspace.yaml"
    data = yaml.safe_load(p.read_text())
    data["groups"][2]["name"] = "Hand edited"
    p.write_text(yaml.safe_dump(data, sort_keys=False))
    bump_mtime(p)
    groups = client.get("/api/workspace").json()["groups"]
    assert groups[2]["name"] == "Hand edited"


def test_reload_after_description_hand_edit(client, example_dir):
    client.get("/api/workspace")
    f = example_dir / "descriptions" / "groups" / "teaching.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("New by hand")
    ws = client.get("/api/workspace").json()
    assert next(g for g in ws["groups"] if g["id"] == "teaching")["description"] == "New by hand"


def test_write_after_hand_edit_keeps_it(client, example_dir):
    p = example_dir / "workspace.yaml"
    p.write_text(p.read_text().replace("name: Teaching", "name: Teaching by hand"))
    bump_mtime(p)
    client.patch("/api/groups/graph-learning", json={"name": "GL"})
    assert "name: Teaching by hand" in p.read_text()


def test_invalid_hand_edit_reports_errors(client, example_dir):
    p = example_dir / "workspace.yaml"
    original = p.read_text()
    p.write_text(original.replace("group: teaching", "group: nowhere", 1))
    bump_mtime(p)
    r = client.get("/api/workspace")
    assert r.status_code == 500 and any("nowhere" in e for e in r.json()["errors"])
    assert client.patch("/api/groups/teaching", json={"name": "x"}).status_code == 500
    p.write_text(original)
    bump_mtime(p)
    assert client.get("/api/workspace").status_code == 200


def test_malformed_yaml_reports_errors(client, example_dir):
    p = example_dir / "workspace.yaml"
    p.write_text("groups: [unclosed\n")
    r = client.get("/api/workspace")
    assert r.status_code == 500 and r.json()["errors"][1].startswith("workspace.yaml")


def test_atomic_write_leaves_no_temp_files(client, example_dir):
    client.patch("/api/groups/teaching", json={"description": "x"})
    leftovers = [p for p in example_dir.rglob(S.TMP_PREFIX + "*")]
    assert leftovers == []


def test_project_reorder_and_move_group(client):
    def order():
        return [(p["id"], p["group"]) for p in client.get("/api/workspace").json()["projects"]]
    before = order()
    assert before[3] == ("graph-sampling", "graph-learning")
    # move to the front of the list
    client.patch("/api/projects/graph-sampling", json={"position": 0})
    assert order()[0] == ("graph-sampling", "graph-learning")
    # move into another group and place it in one call
    r = client.patch("/api/projects/graph-sampling", json={"group": "teaching", "position": 8})
    assert r.status_code == 200
    after = order()
    assert after[8] == ("graph-sampling", "teaching")
    assert [p for p, _ in after if p != "graph-sampling"] == [p for p, _ in before if p != "graph-sampling"]
    # position is not stored as a field
    assert "position" not in client.get("/api/workspace").json()["projects"][8]


def test_group_change_moves_lane_subtree(client, example_dir):
    # spectral-filters has forks journal (-> tutorial) in its group and station-graphs in another group
    r = client.patch("/api/projects/spectral-filters", json={"group": "teaching"})
    assert r.status_code == 200
    groups = {p["id"]: p["group"] for p in client.get("/api/workspace").json()["projects"]}
    assert groups["spectral-filters"] == "teaching"
    assert groups["spectral-filters-journal"] == "teaching"
    assert groups["spectral-filters-tutorial"] == "teaching"  # fork of a fork
    assert groups["station-graphs"] == "climate-statistics"  # already in another group: stays
    assert groups["graph-sampling"] == "graph-learning"  # not a fork: stays
    # one change, one undo step
    assert len(list((example_dir / ".history").iterdir())) == 1
    client.post("/api/undo")
    groups = {p["id"]: p["group"] for p in client.get("/api/workspace").json()["projects"]}
    assert groups["spectral-filters-journal"] == groups["spectral-filters-tutorial"] == "graph-learning"


def test_moving_a_fork_takes_only_its_own_subtree(client):
    client.patch("/api/projects/spectral-filters-journal", json={"group": "teaching"})
    groups = {p["id"]: p["group"] for p in client.get("/api/workspace").json()["projects"]}
    assert groups["spectral-filters-journal"] == groups["spectral-filters-tutorial"] == "teaching"
    assert groups["spectral-filters"] == "graph-learning"
