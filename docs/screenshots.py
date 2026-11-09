"""Take the documentation screenshots (docs/assets/screenshots/*.png).

    make screenshots          # = make build, then: .venv/bin/python docs/screenshots.py

Runs lineage on scratch copies of the example data (user "alice", an admin, with the papers
example; a few plain users; and the "lineage" showcase account), drives it with Playwright, and writes one PNG per screenshot. The clock is
fixed, so retaking the screenshots only changes them when the app changed.

Needs: the built frontend (make build), and Playwright (pip install playwright). It uses the
Chromium given by $CHROMIUM, else /usr/bin/chromium if present, else Playwright's own
(`python -m playwright install chromium`).
"""

import math
import re
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "screenshots"
TODAY = datetime(2026, 11, 9, 15, 0)
PASSWORD = "screenshots"
VIEWPORT = {"width": 1440, "height": 860}

sys.path.insert(0, str(ROOT))
from backend.accounts import Accounts, copy_workspace, user_dir  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def prepare(root: Path) -> None:
    acc = Accounts(root)
    copy_workspace(ROOT / "examples" / "papers", user_dir(root, "alice"))
    acc.add("alice", PASSWORD)  # first account: admin
    for name in ("bob", "carol", "dave"):
        acc.add(name, PASSWORD)
    copy_workspace(ROOT / "examples" / "lineage", user_dir(root, "lineage"))
    acc.add("lineage", "lineage", enforce_length=False)


def start_server(root: Path, port: int) -> subprocess.Popen:
    env = {**os.environ, "DATA_DIR": str(root), "LINEAGE_DEMO": "0", "FRONTEND_DIR": str(ROOT / "frontend" / "dist")}
    proc = subprocess.Popen(
        [str(ROOT / ".venv" / "bin" / "uvicorn"), "--factory", "backend.app:create_app", "--port", str(port),
         "--log-level", "warning"], cwd=ROOT, env=env)
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version")
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    sys.exit("the backend did not start")


def chromium_path() -> str | None:
    if os.environ.get("CHROMIUM"):
        return os.environ["CHROMIUM"]
    return "/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else None


# ------------------------------------------------------------------ helpers


def settle(page: Page, ms: int = 350) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def shot(page: Page, name: str, target=None, *, pad: int = 0) -> None:
    path = OUT / f"{name}.png"
    settle(page)
    if target is None:
        page.screenshot(path=path)
    else:
        box = target.bounding_box()
        clip = {"x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
                "width": box["width"] + 2 * pad, "height": box["height"] + 2 * pad}
        page.screenshot(path=path, clip=clip)
    print("  ", path.relative_to(ROOT))


def content_shot(page: Page, name: str, container: str, *, pad: int = 12) -> None:
    """Screenshot a container, cropped to the bottom of its content (panels are full height)."""
    settle(page)
    el = page.locator(container).first
    box = el.bounding_box()
    bottom = el.evaluate("(e) => Math.max(...[...e.children].map((c) => c.getBoundingClientRect().bottom))")
    height = min(box["height"], bottom - box["y"] + pad)
    page.screenshot(path=OUT / f"{name}.png", clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": height})
    print("  ", (OUT / f"{name}.png").relative_to(ROOT))


def fit_timeline(page: Page, after: str | None = None, before: str | None = None) -> None:
    """Zoom the timeline (with the mouse wheel, like a user) so the visible milestones fill its width."""
    svg = page.locator("svg[aria-label=Timeline]")
    sbox = svg.bounding_box()
    nodes = page.locator("g.node").all()
    if after or before:  # only milestones in this time window (their tooltip says "title · YYYY-MM-DD HH:MM")
        def at(n):  # the first date (and time) in the tooltip; collapsed marks say "n milestones on DATE: …"
            m = re.search(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?", n.locator("title").text_content() or "")
            return m.group(0).replace(" ", "T") if m else ""
        nodes = [n for n in nodes if (not after or at(n) >= after) and (not before or at(n) <= before)]
    xs = [b["x"] + b["width"] / 2 for b in (n.bounding_box() for n in nodes) if b]
    labels = [b["x"] + b["width"] for b in (t.bounding_box() for t in page.locator("text.label").all()) if b]
    left, right = max(labels) + 40, sbox["x"] + sbox["width"] - 40
    lo, hi = min(xs), max(xs)
    k = (right - left) / max(hi - lo, 1)
    if k <= 1.05:
        return
    anchor = (lo * k - left) / (k - 1)
    page.mouse.move(anchor, sbox["y"] + sbox["height"] / 2)
    total = -math.log2(k) / 0.002  # d3-zoom: scale *= 2 ** (-deltaY * 0.002)
    steps = 10
    for _ in range(steps):
        page.mouse.wheel(0, total / steps)
        page.wait_for_timeout(30)
    page.mouse.move(5, 5)


def zoom_to_hours(page: Page, milestone_id: str) -> None:
    """Zoom in around a milestone until the axis is labelled in hours, keeping it in view."""
    svg = page.locator("svg[aria-label=Timeline]").bounding_box()
    left = svg["x"] + 250  # the plot starts after the 250 px of lane labels
    centre = left + (svg["width"] - 250) / 2
    y = svg["y"] + svg["height"] - 20

    def recentre():
        box = node(page, milestone_id).bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, y)
        page.mouse.down()
        page.mouse.move(centre, y, steps=8)
        page.mouse.up()
        page.wait_for_timeout(60)

    for _ in range(80):
        labels = [t.text_content() or "" for t in page.locator("text.tick").all()]
        # hour labels ("01 PM", "02 PM"…), not just the noon marks d3 puts between days
        if sum(bool(re.fullmatch(r"\d\d (AM|PM)", t)) and t != "12 PM" for t in labels) >= 3:
            break
        box = node(page, milestone_id).bounding_box()
        if not (left + 60 < box["x"] < svg["x"] + svg["width"] - 60):
            recentre()
            box = node(page, milestone_id).bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, y)
        page.mouse.wheel(0, -200)
        page.wait_for_timeout(50)
    recentre()
    page.mouse.move(5, 5)


def node(page: Page, milestone_id: str):
    return page.locator(f'g.node[data-id="{milestone_id}"]')


def only_groups(page: Page, *names: str) -> None:
    """Filter the views to these groups (by name)."""
    page.get_by_role("button", name="Clear filters").click(timeout=1000) if page.get_by_role("button", name="Clear filters").count() else None
    for n in names:
        page.locator(".filters button.chip", has_text=n).first.click()


def go(page: Page, view: str) -> None:
    page.goto(f"{page.url.split('#')[0]}#/{view}")
    settle(page)


def close_panel(page: Page) -> None:
    if page.get_by_role("button", name="Close panel").count():
        page.get_by_role("button", name="Close panel").click()


# ------------------------------------------------------------------ the screenshots


def log_in(page: Page, base: str, name: str, password: str = PASSWORD) -> None:
    page.goto(base)
    if page.get_by_role("button", name="Log out").count():
        page.get_by_role("button", name="Log out").click()
    page.get_by_label("User name").wait_for()
    page.get_by_label("User name").fill(name)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Log in").click()
    page.locator("svg[aria-label=Timeline]").wait_for()
    settle(page)


def take(page: Page, base: str) -> None:
    page.clock.set_fixed_time(TODAY)

    # login
    page.goto(base)
    page.get_by_label("User name").wait_for()
    shot(page, "login", page.locator("form.login"), pad=24)

    # ---------------------------------------------------------------- alice: the papers example
    log_in(page, base, "alice")
    shot(page, "timeline")

    # a project with a description, and the description editor with math
    only_groups(page, "Graph learning")
    page.locator('text.label[data-id="spectral-filters"]').click()
    shot(page, "panel-project")
    page.locator("aside.panel").get_by_role("button", name="Edit description").click()
    page.locator("aside.panel").get_by_role("button", name="Preview").click()
    content_shot(page, "description", "aside.panel")
    close_panel(page)

    # delete: the confirmation lists everything that would go
    page.locator('text.label[data-id="spectral-filters-journal"]').click()
    page.locator("aside.panel").get_by_role("button", name="Delete").click()
    content_shot(page, "delete", "aside.panel")
    close_panel(page)

    # adding a reference: picking a milestone on the timeline
    node(page, "spectral-filters.accepted").click()
    page.locator("aside.panel").get_by_role("button", name="Add reference").click()
    page.wait_for_timeout(200)
    shot(page, "add-reference")
    page.keyboard.press("Escape")
    close_panel(page)

    # filters bar
    shot(page, "filters", page.locator(".filters"), pad=6)
    only_groups(page)

    # status board and dependencies
    go(page, "status")
    shot(page, "status")
    go(page, "deps")
    page.locator("svg.deps").wait_for()
    content_shot(page, "dependencies", "main", pad=16)

    # settings: vocabulary, backup, account, users
    go(page, "settings")
    shot(page, "settings")
    for section, name in (("Backup and restore", "backup"), ("Account", "account"), ("Users", "users")):
        sec = page.locator("section", has=page.locator("h2", has_text=section)).first
        sec.scroll_into_view_if_needed()
        shot(page, name, sec, pad=8)
    go(page, "timeline")

    # ---------------------------------------------------------------- lineage: the repository, in GitHub words
    log_in(page, base, "lineage", "lineage")
    fit_timeline(page)
    shot(page, "timeline-lineage")

    # hover highlighting
    node(page, "feature-accounts.demo-account-and-manage-cli").hover()
    shot(page, "hover")
    page.mouse.move(5, 5)

    # hours: the second day at its times of day
    page.get_by_role("button", name="Hours", exact=True).click()
    page.get_by_role("button", name="Reset zoom").click()
    settle(page)
    zoom_to_hours(page, "main.v0-2-0")
    shot(page, "timeline-hours")
    page.get_by_role("button", name="Days", exact=True).click()

    # collapsed days: each branch's milestones of one day as one mark, and the list behind one
    page.get_by_role("button", name="Reset zoom").click()
    page.get_by_role("button", name="Collapse days").click()
    settle(page)
    fit_timeline(page, before="2026-11-09T23:59")
    shot(page, "timeline-collapsed")
    page.locator('g.node[data-id="main.v0-1-1"]').click()
    content_shot(page, "day-list", "aside.panel")
    close_panel(page)
    page.get_by_role("button", name="Collapse days").click()

    # side panel of a release, then its edit form
    page.get_by_role("button", name="Reset zoom").click()
    node(page, "main.v0-2-0").click()
    settle(page)
    fit_timeline(page)
    shot(page, "panel-milestone")
    page.set_viewport_size({"width": VIEWPORT["width"], "height": 1400})
    page.locator("aside.panel").get_by_role("button", name="Edit", exact=True).click()
    content_shot(page, "edit-milestone", "aside.panel")
    page.set_viewport_size(VIEWPORT)
    close_panel(page)

    # dark mode
    page.get_by_role("button", name="Reset zoom").click()
    while "dark" not in page.locator("button", has_text="Theme:").inner_text():
        page.locator("button", has_text="Theme:").click()
    settle(page)
    fit_timeline(page)
    shot(page, "timeline-dark")


def main() -> None:
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        sys.exit("Build the frontend first: make build")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "data"
        prepare(root)
        port = free_port()
        server = start_server(root, port)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=chromium_path())
                ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1.5, color_scheme="light",
                                          timezone_id="UTC", locale="en-GB")
                take(ctx.new_page(), f"http://127.0.0.1:{port}/")
                browser.close()
        finally:
            server.terminate()
            server.wait()
    shutil.rmtree(ROOT / "docs" / "assets" / "screenshots" / ".tmp", ignore_errors=True)


if __name__ == "__main__":
    main()
