"""Build examples/lineage: lineage's own development history, in GitHub vocabulary.

    .venv/bin/python examples/build_lineage.py

It is built through lineage's own API (so every entity is validated and written by
lineage itself) in a scratch data folder, then copied to examples/lineage/. Rerun it to
regenerate the example after editing the history below.
"""

import logging
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.accounts import Accounts, user_dir  # noqa: E402
from backend.app import create_app  # noqa: E402

GH = "https://github.com/gondoresearch/lineage"
OUT = ROOT / "examples" / "lineage"


def commit(sha):
    return [{"label": f"commit {sha}", "url": f"{GH}/commit/{sha}"}]


def tag(name):
    return [{"label": name, "url": f"{GH}/releases/tag/{name}"}]


def build(c: TestClient) -> None:
    def post(t, body):
        r = c.post(f"/api/{t}", json=body)
        assert r.status_code == 201, (t, body, r.text)
        return r.json()["id"]

    def delete(t, i):
        r = c.delete(f"/api/{t}/{i}")
        assert r.status_code == 204, (t, i, r.text)

    # ------------------------------------------------------------ vocabulary (GitHub words)
    # the starter vocabulary (for papers) is not used here; remove it first, so ids stay plain
    ws = c.get("/api/workspace").json()
    for k in ws["kinds"]:
        delete("kinds", k["id"])
    for t in ("states", "reftypes"):
        for e in ws[t]:
            delete(t, e["id"])
    s_prog = post("states", {"name": "in progress", "line": "solid", "waiting_on": "me",
                             "description": "Commits are being made on the branch."})
    s_rev = post("states", {"name": "in review", "line": "dashed", "waiting_on": "others",
                            "description": "A pull request is open and waits for review."})
    s_disc = post("states", {"name": "under discussion", "line": "dotted", "waiting_on": "me",
                             "description": "An issue is open; nothing is built yet."})
    post("states", {"name": "merged", "line": "solid", "opacity": 0.6, "waiting_on": "nobody",
                    "description": "The branch's work is in main."})
    k_commit = post("kinds", {"name": "commit", "shape": "filled-circle", "size": 0.8, "default_state": s_prog})
    k_pr = post("kinds", {"name": "pull request", "shape": "triangle", "default_state": s_rev,
                          "description": "A pull request opened from the branch."})
    k_release = post("kinds", {"name": "release", "shape": "filled-diamond", "size": 1.3, "default_state": s_prog,
                               "description": "A tagged version."})
    k_issue = post("kinds", {"name": "issue", "shape": "open-circle", "default_state": s_disc})
    post("kinds", {"name": "closed", "shape": "filled-square", "closes": True,
                   "description": "Closed without merging (a pull request or an issue)."})
    r_dep = post("reftypes", {"name": "depends on", "directed": True, "line": "dashed"})
    r_rel = post("reftypes", {"name": "related", "directed": False, "line": "dotted"})
    mk_q = post("markers", {"name": "open question", "icon": "question"})
    post("markers", {"name": "bug", "icon": "warning", "color": "#c62828"})
    post("markers", {"name": "blocked", "icon": "lock"})
    mk_break = post("markers", {"name": "breaking change", "icon": "flag", "color": "#c62828",
                                "description": "Changes the data format: read the upgrade notes."})

    # ------------------------------------------------------------ repository and branch groups
    repo = post("domains", {"name": "gondoresearch/lineage", "color": "#24292f",
                            "description": f"The lineage repository ({GH}): each project is a branch, each "
                                           "milestone a commit, pull request, merge or release."})
    g_main = post("groups", {"name": "main", "domain": repo, "color": "#6b4c9a",
                             "description": "The default branch. Features land here through pull requests; releases are tagged on it."})
    g_feat = post("groups", {"name": "feature branches", "domain": repo, "color": "#2f8f83"})
    g_docs = post("groups", {"name": "docs branches", "domain": repo, "color": "#9a7b4c"})
    g_iss = post("groups", {"name": "issues", "domain": repo, "color": "#c06c2b",
                            "description": "Open questions that are not branches yet."})

    def branch(name, group, first, description="", **kw):
        return post("projects", {"title": name, "group": group, "first_milestone": first,
                                 "description": description, **kw})

    def ms(pid, title, at, kind, **kw):
        return post("milestones", {"project": pid, "title": title, "at": at, "kind": kind, **kw})

    def feature(name, group, origin, commits, pr_at, description=""):
        """A branch: its commits, then a pull request. Returns (branch id, pull request id)."""
        (t0, at0, sha0), *rest = commits
        pid = branch(name, group, {"title": t0, "at": at0, "kind": k_commit, "links": commit(sha0)},
                     description, **{"from": origin})
        for t, at, sha in rest:
            ms(pid, t, at, k_commit, links=commit(sha))
        pr = ms(pid, f"Pull request: {name}", pr_at, k_pr)
        return pid, pr

    def merge(name, at, pr, sha, **kw):
        # A merge commit is a commit; what makes it a merge is that it merges the pull request.
        return ms(main, f"Merge {name}", at, k_commit, merges=[pr], links=commit(sha), **kw)

    # ------------------------------------------------------------ 2026-11-06: 0.1 and 0.1.1
    main = branch("main", g_main, {"title": "Initial version", "at": "2026-11-06T15:58", "kind": k_commit,
                                   "links": commit("eac30ab")},
                  "Backend, timeline, editing, status board and dependencies view arrived in one first commit.",
                  links=[{"label": "repository", "url": GH}])
    first = f"{main}.initial-version"

    _, pr = feature("docs/readme", g_docs, first, [("Rewrite the README", "2026-11-06T16:04", "e06faa6")], "2026-11-06T16:05")
    merge("docs/readme", "2026-11-06T16:07", pr, "e06faa6")

    _, pr = feature("feature/domains", g_feat, first,
                    [("Domains and closing kinds", "2026-11-06T16:40", "8f2ccdd"),
                     ("Per-line editing, dark mode, logo", "2026-11-06T17:02", "8f2ccdd")], "2026-11-06T17:05",
                    "Domains above groups, kinds that close a project, text and style on any single lane line, dark mode and the logo.")
    merge("feature/domains", "2026-11-06T17:08", pr, "8f2ccdd")

    _, pr = feature("feature/docker", g_feat, first, [("Dockerfile and compose file", "2026-11-06T17:25", "129970a")], "2026-11-06T17:28")
    m_docker = merge("feature/docker", "2026-11-06T17:31", pr, "129970a")
    v01 = ms(main, "v0.1", "2026-11-06T17:31", k_release, links=tag("v0.1"))

    _, pr = feature("feature/backup-restore", g_feat, v01, [("Version display, backup and restore", "2026-11-06T17:38", "2b7dee7")],
                    "2026-11-06T17:40", "One .tar.gz per workspace with a version manifest; restoring checks the archive and can be undone.")
    merge("feature/backup-restore", "2026-11-06T17:42", pr, "2b7dee7")
    v011 = ms(main, "v0.1.1", "2026-11-06T17:46", k_release, links=tag("v0.1.1"))

    # ------------------------------------------------------------ 2026-11-09: 0.2.0, 0.2.1, layout fix
    acc, pr_acc = feature("feature/accounts", g_feat, v011,
                          [("Accounts and private workspaces", "2026-11-09T12:20", "0bc301d"),
                           ("Demo account and manage CLI", "2026-11-09T12:45", "0bc301d")], "2026-11-09T13:05",
                          "Built-in accounts, each with a private workspace: scrypt passwords, signed session cookies, "
                          "a demo account and a command line to manage accounts.")
    lazy, pr_lazy = feature("feature/lazy-loading", g_feat, v011,
                            [("Load KaTeX and dagre on demand", "2026-11-09T12:55", "0bc301d")], "2026-11-09T13:00",
                            "The main JavaScript bundle went from 685 kB to 243 kB.")
    site, pr_site = feature("docs/site", g_docs, v011,
                            [("MkDocs site with generated reference", "2026-11-09T13:02", "0bc301d")], "2026-11-09T13:08",
                            "The documentation site on GitHub Pages; field tables, CLI help and the endpoint list are generated from the code.")
    merge("feature/lazy-loading", "2026-11-09T13:12", pr_lazy, "0bc301d")
    m_acc = merge("feature/accounts", "2026-11-09T13:14", pr_acc, "0bc301d")
    merge("docs/site", "2026-11-09T13:15", pr_site, "0bc301d")
    v020 = ms(main, "v0.2.0", "2026-11-09T13:15", k_release, links=tag("v0.2.0"), markers=[mk_break],
              line_text="accounts")

    adm, pr_adm = feature("feature/admin", g_feat, v020, [("Settings → Users", "2026-11-09T13:18", "55a7e3b")], "2026-11-09T13:20",
                          "Admins add users, set passwords, delete users and back up or restore their workspaces.")
    merge("feature/admin", "2026-11-09T13:22", pr_adm, "55a7e3b")
    v021 = ms(main, "v0.2.1", "2026-11-09T13:22", k_release, links=tag("v0.2.1"))

    # more documentation on the same docs branch
    ms(site, "Compose examples", "2026-11-09T13:27", k_commit, links=commit("0ae58a6"))
    pr2 = ms(site, "Pull request: compose examples", "2026-11-09T13:28", k_pr)
    merge("docs/site (compose examples)", "2026-11-09T13:29", pr2, "0ae58a6")
    ms(site, "Screenshots", "2026-11-09T13:36", k_commit, links=commit("7d93dae"))
    pr3 = ms(site, "Pull request: screenshots", "2026-11-09T13:37", k_pr)
    merge("docs/site (screenshots)", "2026-11-09T13:39", pr3, "7d93dae")

    fix, pr_fix = feature("fix/same-day-layout", g_feat, v021,
                          [("Order same-day milestones by history", "2026-11-09T13:50", "0b6136f")], "2026-11-09T13:55",
                          "Same-day forks and merges were drawn on top of each other.")
    m_fix = merge("fix/same-day-layout", "2026-11-09T13:57", pr_fix, "0b6136f")

    # ------------------------------------------------------------ 0.3.0: timestamps
    ts = branch("feature/timestamps", g_feat,
                {"title": "Milestone timestamps", "at": "2026-11-09T14:02", "kind": k_commit, "markers": [mk_break],
                 "links": commit("afa839b")},
                "Milestones get a date and a time; references record when they were made; the timeline gets a Days / Hours switch.",
                **{"from": m_fix})
    ms(ts, "Days / Hours view", "2026-11-09T14:12", k_commit, links=commit("afa839b"))
    ms(ts, "The lineage showcase account", "2026-11-09T14:18", k_commit, links=commit("afa839b"))
    pr_ts = ms(ts, "Pull request: feature/timestamps", "2026-11-09T14:22", k_pr)
    merge("feature/timestamps", "2026-11-09T14:24", pr_ts, "afa839b")
    v030 = ms(main, "v0.3.0", "2026-11-09T14:24", k_release, links=tag("v0.3.0"), markers=[mk_break],
              line_text="timestamps")

    # ------------------------------------------------------------ 0.3.1: collapsing days, zoom limits
    _, pr_col = feature("feature/collapse-days", g_feat, v030,
                        [("Collapse a branch's day into one mark (×n)", "2026-11-09T14:33", "8973c13"),
                         ("List the day's milestones in the side panel", "2026-11-09T14:38", "8973c13")], "2026-11-09T14:41",
                        "Collapse days: each branch's milestones of one day as one mark with a ×n badge.")
    _, pr_zoom = feature("fix/zoom-limits", g_feat, v030,
                         [("Days stop at days, Hours at minutes", "2026-11-09T14:39", "8973c13")], "2026-11-09T14:42")
    ms(main, "Drop the merge kind from this example", "2026-11-09T14:44", k_commit, links=commit("8973c13"))
    merge("feature/collapse-days", "2026-11-09T14:45", pr_col, "8973c13")
    merge("fix/zoom-limits", "2026-11-09T14:45", pr_zoom, "8973c13")
    v031 = ms(main, "v0.3.1", "2026-11-09T14:45", k_release, links=tag("v0.3.1"))

    # ------------------------------------------------------------ 0.3.2: versioned image, default admin
    _, pr_img = feature("feature/versioned-image", g_feat, v031,
                        [("Tag the Docker image with the version", "2026-11-09T14:54", "7b2eced")], "2026-11-09T14:56")
    merge("feature/versioned-image", "2026-11-09T14:58", pr_img, "7b2eced")
    _, pr_adm2 = feature("feature/default-admin", g_feat, v031,
                         [("admin / admin, must change its password", "2026-11-09T15:05", "1d9fcc8")], "2026-11-09T15:11",
                         "Whenever there is no admin, lineage creates admin / admin, which must choose a new password first.")
    merge("feature/default-admin", "2026-11-09T15:13", pr_adm2, "1d9fcc8")
    ms(main, "v0.3.2", "2026-11-09T15:16", k_release, links=tag("v0.3.2"))

    # ------------------------------------------------------------ planned
    ms(main, "v0.4.0", "2026-11-30T12:00", k_release, planned=True)

    iss = branch("#1 Encrypted backups", g_iss,
                 {"title": "Admins should not read user backups", "at": "2026-11-09T13:45", "kind": k_issue,
                  "markers": [mk_q]},
                 "Options:\n\n- **A.** Admin backups are sealed with a server-held key: an admin can store and "
                 "restore them, not read them.\n- **B.** Workspaces encrypted at rest with a key derived from the "
                 "user's password: costs hand edits and password resets.\n\nUndecided.")
    ms(iss, "Sealed admin backups", "2026-11-23T12:00", k_commit, planned=True)

    # ------------------------------------------------------------ references
    post("references", {"type": r_dep, "from": f"{adm}.settings-users", "to": m_acc, "created": "2026-11-09T13:18"})
    post("references", {"type": r_rel, "from": f"{iss}.admins-should-not-read-user-backups", "to": f"{adm}.settings-users",
                        "created": "2026-11-09T13:45"})
    post("references", {"type": r_dep, "from": f"{ts}.milestone-timestamps", "to": m_fix, "created": "2026-11-09T14:20"})
    post("references", {"type": r_rel, "from": f"{site}.mkdocs-site-with-generated-reference", "to": v020,
                        "created": "2026-11-09T13:15"})


def main() -> None:
    logging.disable(logging.WARNING)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "data"
        Accounts(root).add("lineage", "lineage", enforce_length=False, admin=False)
        c = TestClient(create_app(root, frontend_dir=root / "none"), headers={"X-Lineage": "1"})
        assert c.post("/api/login", json={"username": "lineage", "password": "lineage"}).status_code == 200
        build(c)
        src = user_dir(root, "lineage")
        shutil.rmtree(OUT, ignore_errors=True)
        OUT.mkdir(parents=True)
        shutil.copy2(src / "workspace.yaml", OUT / "workspace.yaml")
        if (src / "descriptions").is_dir():
            shutil.copytree(src / "descriptions", OUT / "descriptions")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
