def test_etag_not_modified(client):
    r = client.get("/api/workspace")
    etag = r.headers["etag"]
    r2 = client.get("/api/workspace", headers={"If-None-Match": etag})
    assert r2.status_code == 304 and r2.headers["etag"] == etag
    client.patch("/api/groups/teaching", json={"name": "x"})
    r3 = client.get("/api/workspace", headers={"If-None-Match": etag})
    assert r3.status_code == 200 and r3.headers["etag"] != etag


def test_workspace_has_descriptions_and_derived(client):
    ws = client.get("/api/workspace").json()
    sf = next(p for p in ws["projects"] if p["id"] == "spectral-filters")
    assert "$$" in sf["description"]
    assert ws["derived"]["projects"]["bayesian-rainfall"]["merged"] is True
    assert ws["settings"]["fork_color"] == "#7f7f7f"


def test_from_field_uses_alias(client):
    ws = client.get("/api/workspace").json()
    journal = next(p for p in ws["projects"] if p["id"] == "spectral-filters-journal")
    assert journal["from"] == "spectral-filters.accepted" and "from_" not in journal


def test_patch_unknown_is_404(client):
    r = client.patch("/api/groups/nope", json={"name": "x"})
    assert r.status_code == 404 and r.json() == {"errors": ["Group 'nope' does not exist."]}


def test_patch_null_on_required_field_is_422(client):
    assert client.patch("/api/groups/teaching", json={"name": None}).status_code == 422


def test_create_returns_entity(client):
    r = client.post("/api/reftypes", json={"name": "Extends", "directed": True, "line": "dotted", "color": "#123abc"})
    assert r.status_code == 201
    assert r.json() == {"id": "extends", "name": "Extends", "directed": True, "line": "dotted", "opacity": 1.0, "line_width": 1.4,
                        "color": "#123abc", "description": ""}


def test_openapi_complete(client):
    spec = client.get("/openapi.json").json()
    for t in ("groups", "projects", "milestones", "references", "kinds", "states", "reftypes"):
        assert f"/api/{t}" in spec["paths"] and f"/api/{t}/{{id}}" in spec["paths"]
    assert "/api/undo" in spec["paths"] and "/api/settings" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "HTTPValidationError" not in schemas
    assert "from" in schemas["ProjectCreate"]["properties"]
    assert "first_milestone" in schemas["ProjectCreate"]["properties"]


def test_all_kind_shapes_accepted(client):
    shapes = ["open-circle", "filled-circle", "diamond", "filled-diamond", "square", "filled-square",
              "triangle", "filled-triangle", "star", "filled-star", "arrows", "filled-arrows", "cross"]
    for s in shapes:
        r = client.post("/api/kinds", json={"name": f"k {s}", "shape": s})
        assert r.status_code == 201, r.json()
    assert client.post("/api/kinds", json={"name": "bad", "shape": "hexagon"}).status_code == 422


LINES = ["solid", "dashed", "dotted", "long-dash", "dash-dot", "dash-dot-dot"]


def test_line_patterns_for_states_and_reftypes(client):
    for line in LINES:
        assert client.post("/api/states", json={"name": f"s {line}", "line": line, "waiting_on": "me"}).status_code == 201
        assert client.post("/api/reftypes", json={"name": f"r {line}", "line": line, "directed": True}).status_code == 201
    assert client.post("/api/reftypes", json={"name": "bad", "line": "wavy", "directed": True}).status_code == 422


def test_line_opacity(client):
    r = client.post("/api/reftypes", json={"name": "faint", "line": "dotted", "directed": False})
    assert r.json()["opacity"] == 1.0  # default: fully opaque
    assert client.patch("/api/reftypes/faint", json={"opacity": 0.4}).json()["opacity"] == 0.4
    assert client.patch("/api/states/paused", json={"opacity": 0.5}).json()["opacity"] == 0.5
    for bad in (0, 0.05, 1.5):
        r = client.patch("/api/reftypes/faint", json={"opacity": bad})
        assert r.status_code == 422, bad
        assert r.json()["errors"][0].startswith("opacity:")


def test_kind_size(client):
    r = client.post("/api/kinds", json={"name": "big", "shape": "star"})
    assert r.json()["size"] == 1.0
    assert client.patch("/api/kinds/big", json={"size": 1.4}).json()["size"] == 1.4
    assert client.patch("/api/kinds/big", json={"size": 2.0}).json()["size"] == 2.0  # up to 200%
    for bad in (0.3, 2.1):
        r = client.patch("/api/kinds/big", json={"size": bad})
        assert r.status_code == 422 and r.json()["errors"][0].startswith("size:")



def test_line_widths(client):
    assert client.patch("/api/states/drafting", json={"line_width": 4}).json()["line_width"] == 4
    assert client.patch("/api/reftypes/builds-on", json={"line_width": 0.5}).json()["line_width"] == 0.5
    r = client.patch("/api/settings", json={"fork_width": 3, "merge_width": 2.5})
    assert (r.json()["fork_width"], r.json()["merge_width"]) == (3, 2.5)
    for bad in (0.2, 9):
        assert client.patch("/api/states/drafting", json={"line_width": bad}).status_code == 422
        assert client.patch("/api/settings", json={"fork_width": bad}).status_code == 422


def test_line_text_on_states_and_references(client):
    s = client.get("/api/workspace").json()["states"][0]
    assert (s["text"], s["text_align"], s["text_position"]) == ("", "center", "above")  # off by default
    r = client.patch("/api/states/under-review", json={"text": "waiting for referees", "text_align": "left", "text_position": "below"})
    assert (r.json()["text"], r.json()["text_align"], r.json()["text_position"]) == ("waiting for referees", "left", "below")
    r = client.post("/api/references", json={"type": "builds-on", "from": "graph-sampling.draft", "to": "spectral-filters.published",
                                             "text": "uses Lemma 2", "text_position": "middle"})
    assert r.status_code == 201 and (r.json()["text"], r.json()["text_position"]) == ("uses Lemma 2", "middle")
    assert client.patch(f"/api/references/{r.json()['id']}", json={"text_align": "right"}).json()["text_align"] == "right"
    assert r.json()["text_orientation"] == "horizontal"  # default
    assert client.patch(f"/api/references/{r.json()['id']}", json={"text_orientation": "along"}).json()["text_orientation"] == "along"
    assert client.patch(f"/api/references/{r.json()['id']}", json={"text_orientation": "diagonal"}).status_code == 422
    assert client.patch("/api/states/paused", json={"text_position": "sideways"}).status_code == 422


def test_line_text_per_milestone(client):
    ms = client.get("/api/workspace").json()["milestones"][0]
    assert (ms["line_text"], ms["line_text_align"], ms["line_text_position"]) == ("", "center", "above")
    r = client.patch("/api/milestones/station-graphs.preprint",
                     json={"line_text": "waiting for Ana's data", "line_text_align": "left", "line_text_position": "below"})
    assert r.status_code == 200
    assert (r.json()["line_text"], r.json()["line_text_align"], r.json()["line_text_position"]) == ("waiting for Ana's data", "left", "below")
    # only that milestone carries it; the shared state is untouched
    ws = client.get("/api/workspace").json()
    assert [m["id"] for m in ws["milestones"] if m["line_text"]] == ["station-graphs.preprint"]
    assert next(s for s in ws["states"] if s["id"] == "with-co-authors")["text"] == ""
    # can be set when creating a milestone too
    r = client.post("/api/milestones", json={"project": "graph-course", "title": "x", "at": "2026-10-20", "kind": "draft",
                                             "line_text": "next step"})
    assert r.status_code == 201 and r.json()["line_text"] == "next step"


def test_line_text_size(client):
    assert client.get("/api/workspace").json()["states"][0]["text_size"] == 10
    assert client.patch("/api/states/drafting", json={"text_size": 14}).json()["text_size"] == 14
    assert client.patch("/api/references/builds-on", json={"text_size": 8}).json()["text_size"] == 8
    assert client.patch("/api/milestones/graph-sampling.draft", json={"line_text_size": 18}).json()["line_text_size"] == 18
    for bad in (6, 25):
        assert client.patch("/api/states/drafting", json={"text_size": bad}).status_code == 422


def test_line_look_per_milestone(client):
    m = client.get("/api/workspace").json()["milestones"][0]
    assert [m[k] for k in ("line_pattern", "line_color", "line_width", "line_opacity")] == [None, None, None, None]
    r = client.patch("/api/milestones/station-graphs.preprint",
                     json={"line_pattern": "dash-dot", "line_color": "#123456", "line_width": 5, "line_opacity": 0.6})
    assert r.status_code == 200
    assert [r.json()[k] for k in ("line_pattern", "line_color", "line_width", "line_opacity")] == ["dash-dot", "#123456", 5, 0.6]
    # back to the state's look
    r = client.patch("/api/milestones/station-graphs.preprint", json={"line_pattern": None, "line_color": None})
    assert (r.json()["line_pattern"], r.json()["line_color"]) == (None, None)
    assert client.patch("/api/milestones/station-graphs.preprint", json={"line_color": "blue"}).status_code == 422
    assert client.patch("/api/milestones/station-graphs.preprint", json={"line_width": 20}).status_code == 422
