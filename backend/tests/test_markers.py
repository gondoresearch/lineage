ICONS = ["warning", "question", "chain", "flag", "pin", "clock", "lock", "check", "info"]


def test_create_marker_and_assign(client, example_dir):
    r = client.post("/api/markers", json={"name": "Needs data", "icon": "warning", "color": "#cc8800",
                                          "description": "Waiting for the *new* run."})
    assert r.status_code == 201
    assert r.json() == {"id": "needs-data", "name": "Needs data", "icon": "warning", "color": "#cc8800",
                        "description": "Waiting for the *new* run."}
    assert (example_dir / "descriptions" / "markers" / "needs-data.md").read_text() == "Waiting for the *new* run."
    r = client.patch("/api/milestones/graph-sampling.draft", json={"markers": ["needs-data"]})
    assert r.status_code == 200 and r.json()["markers"] == ["needs-data"]


def test_all_icons_accepted(client):
    for icon in ICONS:
        assert client.post("/api/markers", json={"name": f"m {icon}", "icon": icon}).status_code == 201
    assert client.post("/api/markers", json={"name": "bad", "icon": "skull"}).status_code == 422


def test_unknown_marker_rejected(client):
    r = client.patch("/api/milestones/graph-sampling.draft", json={"markers": ["nope"]})
    assert r.status_code == 422
    assert any("markers 'nope'" in e for e in r.json()["errors"])


def test_marker_delete_blocked_while_in_use(client):
    client.post("/api/markers", json={"name": "Linked", "icon": "chain"})
    client.patch("/api/milestones/graph-sampling.draft", json={"markers": ["linked"]})
    r = client.delete("/api/markers/linked")
    assert r.status_code == 409
    assert r.json()["blockers"] == [{"type": "milestones", "id": "graph-sampling.draft", "reason": "has this marker"}]
    client.patch("/api/milestones/graph-sampling.draft", json={"markers": []})
    assert client.delete("/api/markers/linked").status_code == 204


def test_markers_in_workspace_and_openapi(client):
    ws = client.get("/api/workspace").json()
    assert "markers" in ws
    assert all("markers" in m for m in ws["milestones"])
    spec = client.get("/openapi.json").json()
    assert "/api/markers" in spec["paths"] and "/api/markers/{id}" in spec["paths"]
