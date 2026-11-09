# lineage: manual test plan

A checklist to verify lineage by hand. Each item is an action followed by the expected result (→). Tick the boxes as you go; note anything unexpected next to the item.

Work on a **scratch data folder**, never on your real `data/` folder. Most sections assume you are logged in as **demo** (password **demo**), whose workspace is a copy of the example data (`examples/papers`); its projects, groups and milestones are named below. That workspace lives in `/tmp/lineage-test/users/demo/`; "`workspace.yaml`" and "`descriptions/`" below mean the files there.

## 0. Setup

### From source

- [ ] `python -m venv .venv && .venv/bin/pip install -e "./backend[test]"` and `cd frontend && npm install` → both finish without errors.
- [ ] `rm -rf /tmp/lineage-test` → no scratch folder yet.
- [ ] `DATA_DIR=/tmp/lineage-test .venv/bin/uvicorn --factory backend.app:create_app` → "Created the demo account" and a warning about its password, then "Application startup complete" on http://127.0.0.1:8000.
- [ ] In another terminal, `cd frontend && npm run dev` → Vite prints http://localhost:5173; open it → the login page. Log in as demo / demo → the timeline with the example projects.
- [ ] Alternatively `cd frontend && npm run build`, then reload http://localhost:8000 → the same app, served by the backend alone.

### Resetting between sections

- [ ] To start a section from a clean state: stop the backend, `rm -rf /tmp/lineage-test`, start it again, reload the page and log in as demo again.
- [ ] Useful while testing: keep `/tmp/lineage-test/users/demo/workspace.yaml` open in an editor, and `ls /tmp/lineage-test/users/demo/.history` to see snapshots.

## 1. Automated tests

- [ ] `cd backend && ../.venv/bin/pytest` → all tests pass.
- [ ] `cd frontend && npm test` → all tests pass.
- [ ] `cd frontend && npx tsc --noEmit -p .` → no output (no type errors).
- [ ] `make build` → "built", with no warnings; the main `index-*.js` is about 240 kB, with `markdown-*.js` and `Dependencies-*.js` as separate chunks.

## 2. Data folder, seed and hand edits

- [ ] `rm -rf /tmp/lineage-empty && printf 'testpass1\n' | DATA_DIR=/tmp/lineage-empty LINEAGE_DEMO=0 .venv/bin/python -m backend.manage adduser test --password-stdin`, start the backend with `DATA_DIR=/tmp/lineage-empty` and log in as test / testpass1 → `/tmp/lineage-empty/users/test/workspace.yaml` is created; the page shows no projects; Settings lists the starter vocabulary: kinds draft, preprint, submitted, revision, accepted, published, rejected, closed; states drafting, revising, with co-authors, under review, paused, accepted, published; reference types builds on, companion. There is no "closed" state.
- [ ] In the starter vocabulary, preprint is an empty star, submitted a triangle, published a full star, closed a filled square, and closed is marked "closes the project".
- [ ] With the page open, edit a project title in `workspace.yaml` and save → within about 5 seconds the timeline shows the new title, without losing zoom, filters or the open side panel.
- [ ] Edit a description file under `descriptions/` → the side panel shows the new text within about 5 seconds.
- [ ] Break `workspace.yaml` (e.g. set a project's `group` to `nowhere`) → a red banner lists the problem; making any change in the app fails with the same messages.
- [ ] Fix the file → the banner disappears within about 5 seconds and the app works again.
- [ ] Write invalid YAML (e.g. `groups: [unclosed`) → the banner shows a `workspace.yaml:` parse error; fixing it recovers.
- [ ] Old format: in the scratch workspace, add a state with id `closed` and set a milestone's state to `closed`, then reload → the state is gone, a "closed" kind exists, and that milestone has kind closed and no state.

## 3. Timeline basics

- [ ] Lanes are grouped: groups without a domain first (Teaching, in the example data), then each domain with a heading row (RESEARCH) and its groups (Graph learning, Climate statistics); every group has its own heading row.
- [ ] Within a group, forks sit directly under their origin and are indented: Spectral filters → journal version → tutorial.
- [ ] Station-graphs (forked from Spectral filters, but in Climate statistics) is a top-level lane in its own group, with a fork curve coming from the Spectral filters lane.
- [ ] Fork and merge curves leave the source milestone vertically and enter the target horizontally; lines stop at symbol edges and never run through a symbol.
- [ ] Reference lines are drawn underneath lanes, curves and symbols; "builds on" has an arrowhead pointing at the work being built on; "companion" has none.
- [ ] A red vertical "today" line is visible; lanes of projects waiting on someone continue as a line up to today; finished, closed or merged projects stop at their last milestone.
- [ ] Planned milestones are faded; the overdue one (Fast graph sampling → submit) has a small red dot.
- [ ] Lines to future planned milestones are faded and start at today.
- [ ] Scroll on the timeline → zooms horizontally around the pointer; drag on the timeline → pans; the label column stays fixed.
- [ ] Toggle **Event order** → every distinct date gets equal spacing; the "today" line sits between its neighbouring dates; zoom resets. Toggle **Time** back.
- [ ] **Reset zoom** → back to the full view.
- [ ] Axis labels never overlap each other or the "today" label, and none are cut at the edges.
- [ ] Long project titles end with "…" and do not spill past the label column; hovering shows the full title.
- [ ] The legend lists groups, kinds (with their shapes and sizes), states (pattern, colour, opacity, thickness), references, fork/merge lines, markers, planned/overdue and today.
- [ ] Switch to another view and back → zoom and pan are kept.

### Days and hours (0.3)

- [ ] Log in as **lineage** / **lineage** → branches under *gondoresearch/lineage*; feature branches fork from *main* and their pull requests are merged back by merge commits; nothing overlaps.
- [ ] **Hours** → the label "today" becomes "now"; scroll-zoom into 9 November → the axis shows hours, then half-hours and minutes; each commit sits at its time (hover shows it).
- [ ] **Days** → back to whole days; same-day steps keep their history order.
- [ ] Open a milestone's **Edit** → "Date and time" shows its time; change it to an earlier time on the same day → it moves left in Hours.
- [ ] **Add milestone** → date and time start at the current time.
- [ ] **Add reference** → a "Recorded" field with the current time; the reference's panel shows it; references from before 0.3 say "unknown".
- [ ] Open a milestone (side panel open) → the whole timeline stays in view.
- [ ] As lineage, **Collapse days** → each branch shows one mark per day with ×n (e.g. main ×7 on 6 November, drawn as v0.1.1); forks come out to its right, merges curve back into it; the button is disabled in Hours.
- [ ] Click main's ×7 → the side panel lists the seven milestones with symbol, kind, state and time; click one → it opens. Turn the toggle off → all milestones are drawn again.

## 4. Selecting and the side panel

- [ ] Click a milestone symbol → the side panel shows it (project, date, kind, state, markers, labels, merges, links, colour, description) and a blue ring around it on the timeline.
- [ ] Click a project label → the project panel (group, forked from, current state, milestone list, links, colour, description); the label turns bold and blue.
- [ ] Click a reference line (also the thin dotted ones) → the reference panel; the line is drawn thicker.
- [ ] Click a group or domain heading on the timeline → its panel.
- [ ] Links inside panels (e.g. a milestone's project) open that entity's panel.
- [ ] Close the panel with × → selection highlights disappear.

## 5. Creating, editing and deleting (every entity type)

For each type below: create one, edit it, check the change on screen and in `workspace.yaml`, then delete it. After each change a toast appears with **Undo**.

- [ ] **Domain** (Settings → Domains → New domain): name, optional colour, description → appears in the list; ↑/↓ reorder it; delete an empty one → gone.
- [ ] **Group** (toolbar Add group or Settings): name, colour (required, no Clear), domain → its heading appears under the chosen domain; change the domain in Edit → the group, with its projects, moves under the new domain's heading; choose "(none)" → it moves to the top.
- [ ] **Project** (toolbar Add project): title, group, first milestone (title, date, kind, state "(default)") → a new lane at the bottom of its group.
- [ ] **Milestone** (project panel → Add milestone): title, date, kind, state, planned, labels, markers, links, colour, line text → appears on the lane in date order.
- [ ] **Reference** (milestone panel → Add reference, see section 7).
- [ ] **Kind / State / Reference type / Marker** (Settings → New …) → each appears in its list and in the legend.
- [ ] Rename anything → its id in `workspace.yaml` does not change.
- [ ] Ids of new entities are slugs of their name (e.g. "My Group" → `my-group`, a second one → `my-group-2`); milestone ids are `<project>.<title-slug>`.
- [ ] Descriptions: Edit description → type Markdown with `$x^2$` and `$$\int_0^1 f$$`, toggle **Preview** → rendered math; Save → `descriptions/<type>/<id>.md` contains exactly the text; empty the description and save → the file is deleted.
- [ ] Links in descriptions open in a new tab.

### Validation (errors shown next to the form; nothing written)

- [ ] Edit a project (e.g. Spectral filters: a tutorial) and set **Forked from** to a milestone dated after its first milestone → a red message under the form; `workspace.yaml` unchanged.
- [ ] Create a milestone of kind preprint in a new, non-forked project with state "(default)" → "has no state" error (preprint has no default state and there is nothing to inherit).
- [ ] A kind that closes the project needs no state: create a milestone of kind closed → no state field; it saves.
- [ ] Enter a colour that is not #RRGGBB by hand-editing YAML → the banner reports it.
- [ ] Create a directed reference that would make a cycle (a milestone building on a later milestone of its own lineage) → "History has a cycle" error.

### Deleting

- [ ] Delete **Spectral filters for graph networks** → the confirmation lists blockers (journal version and weather stations fork from it); Delete is disabled; blockers are links.
- [ ] Delete group **Teaching** → blocked by its projects.
- [ ] Delete kind **submitted** / state **under review** / reference type **companion** / a marker in use → blocked, listing what uses it.
- [ ] Delete a domain with groups → blocked by its groups.
- [ ] Delete a project with no forks or merges (Graph learning mini-course) → the confirmation lists the project, its milestones and its references; confirm → all gone, description files removed.
- [ ] Delete a milestone that has a description (Spectral filters: a tutorial › on hold) → gone, its `.md` file deleted.
- [ ] Delete a project's only milestone → blocked ("this is the project's only milestone").

## 6. Undo and toasts

- [ ] After any change, click **Undo** in the toast → the change is reverted, including description files.
- [ ] Toolbar **Undo** repeatedly → walks back one change at a time; when there is nothing left → "Nothing to undo."
- [ ] `ls .history` → one snapshot per change, at most 20.
- [ ] The toast disappears by itself after a few seconds.

## 7. Fork, merge and reference flows

- [ ] Milestone panel → **Fork from here** → the project form with "Forked from" preset; create → new lane directly under the origin (if in the same group), with a fork curve; the source milestone keeps its ring while the form is open.
- [ ] Milestone panel → **Merge into…** → choose target project, title, date (not before the source) → a merge curve from the source into the new milestone.
- [ ] Merge with a date before the source → error under the form.
- [ ] Milestone panel → **Add reference** → a dashed banner above the timeline asks you to click the target; milestones show a crosshair and glow on hover.
- [ ] Click the source milestone itself → "That is the source milestone; pick another one." and picking continues.
- [ ] Click another milestone → the form shows "Project › milestone" as target; **Pick again** lets you change it; choose a type and Add → a new reference line.
- [ ] Start Add reference and press **Esc** (or the banner's Cancel) → picking stops, the form stays; Add without a target → "Click the target milestone on the timeline first."
- [ ] While picking, clicking project labels or reference lines does nothing.
- [ ] Reference form: line text, along-the-line position (near source / middle / near target), relative position (above / on / below), size, text direction **horizontal** or **along the line** → on the timeline the text follows the setting; "along the line" text follows the line's angle and is never upside down.

## 8. Moving projects (drag lane labels)

- [ ] Click a project label (no drag) → selects it (drag needs more than a few pixels of movement).
- [ ] Drag **Fast graph sampling** above Spectral filters → a blue insertion line follows; drop → it moves to the top of Graph learning; toast "Moved …".
- [ ] Drag **Spectral filters for graph networks** to the end of another group → the project **and its forks** (journal version, tutorial) move together, still nested; toast says "and 2 forks"; weather stations (already in another group) stays put.
- [ ] Drag a fork into another group → it becomes a top-level lane there; its own forks come with it.
- [ ] Drop a project where its order would not change (e.g. just below itself) → nothing happens, no toast.
- [ ] Undo after a move → back in place in one step.
- [ ] Changing the Group field in a project's Edit form behaves the same way (the subtree moves along).

## 9. Lane lines (state lines)

- [ ] Click a lane line → the **Line** panel: "After X, until Y", a preview, the line's state, "Look of this line" and "Text on this line"; only Save and Cancel (no "Edit state" or "Delete state").
- [ ] Only the clicked line is highlighted (and its faded part past today, if any), plus the ring on the milestone it follows.
- [ ] Change the **State** → Save → only that line changes; Undo works.
- [ ] Set pattern, colour, thickness and opacity → Save → only that line changes; other lines in the same state do not; the state in Settings is unchanged.
- [ ] **Reset** / **Clear** → that setting goes back to the state's value.
- [ ] **Text on this line** with alignment, position and size → shown only on that line; hidden if the line is too short for it.
- [ ] Settings → States → open a state → all lines in that state are highlighted; its "Default text on every line in this state" shows on every line that has no text of its own.
- [ ] The milestone form has the same "Text on the line after this milestone" fields.

## 10. Vocabulary details

- [ ] **Shapes**: give kinds each shape in turn (open-circle, filled-circle, diamond, filled-diamond, square, filled-square, triangle, filled-triangle, star, filled-star, arrows, filled-arrows, cross) → each draws correctly in the timeline, legend and Settings; lines stop at the edges.
- [ ] **Kind size**: 50 % to 200 % slider with preview → symbols resize; lines still stop at their edges; marker badges stay inside the lane at 200 %.
- [ ] **Closing kind**: tick "Closes the project" → its milestones have no state; the lane ends at them; no line to today; the project is "closed" on the status board and counts as inactive.
- [ ] **States**: pattern (solid, dashed, long dash, dotted, dash-dot, dash-dot-dot), colour, opacity, thickness, waiting on (me / others / nobody) → lane lines and the legend follow.
- [ ] **Reference types**: directed (arrow), pattern, colour, opacity, thickness → reference lines and the legend follow.
- [ ] **Markers**: create one with each icon (warning, question, chain, flag, pin, clock, lock, check, info) and a colour; tick it on a milestone → a badge at the symbol's upper right (after the overdue dot), full strength even on planned milestones; clicking the badge selects the milestone; the legend lists it.
- [ ] **Fork and merge lines** (Settings): colours (with Clear → project colour) and thicknesses → curves follow.
- [ ] **Colours** follow their chains: milestone → kind → project → group; lane line → the line's own colour → state → project → group; reference → reference type → gray; Clear on any colour falls back to the next in its chain.

## 11. Status board

- [ ] Three columns: **On me**, **On others**, **Inactive** (waiting on nobody, closed, or nothing has happened yet).
- [ ] Each card: title, group, **Current state** (name and time in state), **Current milestone** (title and date), **Next** (next planned milestone; red with "overdue" if overdue).
- [ ] Cards sorted by time in state, longest first.
- [ ] Bayesian rainfall model reads "closed · …".
- [ ] Click a card → the project panel; hover a card → related projects stay bright, the rest dims.

## 12. Dependencies view

- [ ] Projects as boxes in their colours; earlier work below the work that forks, merges or builds on it.
- [ ] Forks and merges as solid lines; references with their type's pattern; "builds on" arrows point at the work built on.
- [ ] Several references of one type between two projects show as one line (hover shows "×N").
- [ ] Click a box → project panel; hover → related projects stay bright.

## 13. Hover highlighting

- [ ] Timeline: hover `spectral-filters.accepted` → its ancestors (earlier Spectral filters milestones), descendants (published, the journal version and tutorial, the mini-course which builds on published) stay bright; the weather-stations fork (from an earlier milestone) dims.
- [ ] Hovering a milestone with a companion reference also lights up its companion partner (but not partners of its ancestors).
- [ ] Moving the pointer away clears the dimming.

## 14. Filters

- [ ] Group chips → only those groups' lanes / cards / boxes; domains without visible groups disappear.
- [ ] State chips → only projects whose current state is selected.
- [ ] **Hide inactive** → inactive projects disappear.
- [ ] Filters persist when switching between timeline, status and dependencies; **Clear filters** resets them.
- [ ] With a filter hiding everything → "No project matches the filters."

## 15. Dark mode and theme

- [ ] With the system in dark mode and the toolbar on **Theme: auto** → dark background, readable text, readable domain headings, error and confirmation boxes still clearly red.
- [ ] Toolbar button cycles **auto → light → dark → auto**; reload → the choice is remembered (not for auto).
- [ ] Forms, colour pickers, the toast and the side panel are readable in both themes.

## 16. Backup and restore

- [ ] Toolbar shows **lineage v0.3.2** (the backend version) next to the logo; `curl localhost:8000/api/version` returns the same.
- [ ] Settings → **Download a backup** → the browser downloads `lineage-backup-<version>-<date>-<time>.tar.gz`.
- [ ] `tar -tzf <file>` → `lineage-backup.json`, `workspace.yaml`, `descriptions/…`; no `.history`.
- [ ] `tar -xzOf <file> lineage-backup.json` → app "lineage", format 1, the version and the creation time.
- [ ] Make some changes (rename a group, delete a reference), then **Restore from a backup…** → choose the file → a red box: "Restoring this file overwrites the current database", with the file name and size → **Cancel** → nothing changes.
- [ ] Repeat and **Overwrite and restore** → the earlier state is back (group name, deleted reference, description files); toast with the backup's date and version.
- [ ] **Undo** right after a restore → the changes from before the restore are back.
- [ ] Edit the backup's `lineage-backup.json` to another version (e.g. `0.0.9`), re-pack it, restore → a second warning "This backup is from another lineage version" showing both versions; **Restore anyway** works.
- [ ] Restore a file that is not a `.tar.gz` → "This is not a .tar.gz file."; nothing changes.
- [ ] Restore a `.tar.gz` without `lineage-backup.json` → "This is not a lineage backup"; nothing changes.
- [ ] Restore an archive containing `../something` or an extra file (e.g. `run.sh`) → rejected; nothing changes.
- [ ] Restore a backup whose `workspace.yaml` is invalid → "The backup is not a valid workspace" with the reasons; nothing changes.
- [ ] Break `workspace.yaml` by hand (red banner), then restore a good backup → the app works again.

## 17. Docker

- [ ] `printf 'LINEAGE_UID=%s\nLINEAGE_GID=%s\n' $(id -u) $(id -g) > .env` → `.env` with your ids.
- [ ] `mkdir data`, then `docker compose up -d` → the image builds and the container starts; `docker compose ps` shows it running; `docker compose logs` shows "Created the demo account".
- [ ] http://localhost:8080 → the login page; demo / demo → the example projects, with the version in the toolbar.
- [ ] `docker compose exec -it lineage python -m backend.manage adduser alice` → asks for the password twice; log out, log in as alice → an empty workspace.
- [ ] From another machine on the network, http://<this-machine>:8080 → not reachable (published on 127.0.0.1 only).
- [ ] Create a project, `docker compose restart` → the project is still there.
- [ ] `ls -l data` → files owned by your user, not root.
- [ ] Edit `data/users/demo/workspace.yaml` on the host → the page shows the change within about 5 seconds.
- [ ] Disconnect from the internet and reload → the app works fully (only http://localhost:8080/docs needs internet, for its scripts).
- [ ] Download a backup and restore it inside the container → works as in section 16.
- [ ] `docker compose down && docker compose up -d` → data still there; `restart: unless-stopped` brings it back after a reboot.
- [ ] Without `.env` on a machine where your ids are not 1000 → lineage cannot write to `data/` (expected; the README explains the fix).

## 18. Accounts

Start from a clean `/tmp/lineage-test` (demo is created). Add two users: `printf 'alicepass\n' | DATA_DIR=/tmp/lineage-test .venv/bin/python -m backend.manage adduser alice --password-stdin`, and the same for `bob` with `bobpass1`.

- [ ] Open the app without logging in → the login page, nothing else; `curl -i localhost:8000/api/workspace` → 401 `{"errors": ["Not logged in."]}`.
- [ ] Wrong password → "Wrong user name or password."; unknown user → the same message.
- [ ] Six wrong passwords in a row for alice → "Too many failed attempts. Try again in 30 s."; even the right password is refused until then.
- [ ] Log in as alice → an empty workspace with the starter vocabulary; her name and **Log out** in the toolbar. Create a group "Alice's".
- [ ] Log out → the login page. Log in as bob → no "Alice's" group; Undo says there is nothing to undo.
- [ ] Reload the page while logged in → still logged in (the session lasts 30 days).
- [ ] Settings → **Account** shows "Logged in as bob". Change the password with a wrong current password → an error; with a 5-character new one → the button stays disabled; with a proper one → a toast, and you stay logged in.
- [ ] Log in as bob in a second browser (or a private window) before changing his password → after the change, that window shows the login page within about 5 seconds.
- [ ] `DATA_DIR=/tmp/lineage-test .venv/bin/python -m backend.manage passwd alice` while she is logged in → her page shows the login page within about 5 seconds.
- [ ] `… manage deluser bob` → bob is logged out; `/tmp/lineage-test/users/bob/` is still there. `… manage deluser bob` again → "does not exist".
- [ ] `… manage list` → alice, demo.
- [ ] A download of the backup as alice contains only alice's data.
- [ ] Old layout: `rm -rf /tmp/lineage-old && cp -r examples/papers /tmp/lineage-old`, start the backend with `DATA_DIR=/tmp/lineage-old` → a warning in the log about a workspace from before accounts; demo is created anyway. Stop it, then `printf 'oldpass1\n' | DATA_DIR=/tmp/lineage-old .venv/bin/python -m backend.manage adduser old --adopt --password-stdin` → `workspace.yaml` and `descriptions/` moved to `/tmp/lineage-old/users/old/`; log in as old → the example projects.
- [ ] `LINEAGE_DEMO=0` on a fresh folder → no showcase accounts; only **admin**, created with a warning to change its password.

### Admin

- [ ] A fresh start created **admin** (`… manage list` → `admin  (admin)`). Log in as admin / admin → only a **Choose a new password** screen; `curl -b <cookie> localhost:8000/api/workspace` → 403 "Choose a new password first."; set one (8+ characters) → the app appears with **Users**.
- [ ] `… manage admin alice on` → alice is an admin too (`… manage list` → `alice  (admin)`); demo and bob are not.

- [ ] Log in as bob → Settings has no **Users** section; `curl -b <bob's cookie> localhost:8000/api/admin/users` → 403.
- [ ] Log in as alice → Settings → Account says "(admin)"; **Users** lists alice (admin, "you"), bob and demo, with **Set password**, **Backup…** and **Delete** on bob and demo only.
- [ ] **Add a user** carol / carolpass → listed; log in as carol in a private window → an empty workspace. A name like `Carol` or a 5-character password → the button stays disabled or an error explains why.
- [ ] **Set password** for carol → toast; carol's window shows the login page within about 5 seconds; the new password works.
- [ ] Log in as bob, make a change. As alice, bob → **Backup…** → **Download a backup** → `lineage-backup-bob-….tar.gz` with only bob's data. Have bob change something else, then as alice restore that file into bob → bob's page shows the backed-up state within about 5 seconds; bob's **Undo** brings his change back; alice's own workspace is unchanged.
- [ ] **Delete** carol without "Also delete their workspace" → gone from the list, logged out; `/tmp/lineage-test/users/carol/` is still there. Add carol again → her old workspace is back. Delete her with the box ticked → the folder is gone.
- [ ] `… manage admin bob on` → after a reload bob sees **Users**; alice's list now shows bob as admin with no buttons. `… manage admin bob off` → bob's **Users** section is gone after a reload, and his admin calls get 403 at once.
- [ ] `… manage admin demo on` → refused while demo's password is `demo`.

## 19. API checks (optional)

Log in first and keep the cookie: `curl -c /tmp/cj -X POST localhost:8000/api/login -H 'X-Lineage: 1' -H 'Content-Type: application/json' -d '{"username":"demo","password":"demo"}'`. Pass `-b /tmp/cj` to every command below.

- [ ] http://localhost:8000/docs (or :8080/docs) → every endpoint listed: workspace, the eight entity types (create / edit / delete), settings, undo, version, backup, restore, login, logout, me, password.
- [ ] `curl -i localhost:8000/api/workspace` → an `ETag` header; repeat with `-H 'If-None-Match: <etag>'` → `304 Not Modified`.
- [ ] `curl -X DELETE -H 'X-Lineage: 1' 'localhost:8000/api/projects/spectral-filters?dry_run=true'` → `removes` and `blockers`, nothing deleted.
- [ ] `curl -X PATCH -H 'X-Lineage: 1' localhost:8000/api/groups/teaching -H 'Content-Type: application/json' -d '{"group":"x"}'` → 422 with `{"errors": […]}`.
- [ ] `curl -X POST localhost:8000/api/undo` (cookie but no `X-Lineage` header) → 403.

## 20. Known limitations (not bugs, but worth watching)

- [ ] Line text and marker badges can crowd each other where many lines meet.
- [ ] Projects cannot be dragged into a group that has no projects yet (use the project's Edit form).
- [ ] Groups cannot be dragged between domains (use the group's Edit form).
- [ ] The first description shown (and the first visit to Dependencies) loads an extra chunk; on a slow connection the text or graph appears a moment later.
- [ ] Restore warns on any version difference, even a patch release.
