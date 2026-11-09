"""MkDocs hook: fills generated reference sections from the code, so they cannot drift.

In a page, a line consisting only of one of these markers is replaced:

    <!-- gen:fields Project -->     field table of a stored entity (backend/models.py)
    <!-- gen:cli -->                 `python -m backend.manage --help` and each command's help
    <!-- gen:api -->                 the HTTP endpoints (from the app's OpenAPI schema)
"""

import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MARKER = re.compile(r"^<!-- gen:(\w+)(?: (\w+))? -->$", re.M)


def _type(prop: dict, defs: dict) -> str:
    if "$ref" in prop:
        return _type(defs[prop["$ref"].split("/")[-1]], defs)
    if "enum" in prop:
        return " \\| ".join(f"`{v}`" for v in prop["enum"])
    if "const" in prop:
        return f"`{prop['const']}`"
    if "anyOf" in prop:
        parts = [_type(p, defs) for p in prop["anyOf"]]
        return " or ".join(parts)
    t = prop.get("type", "")
    if t == "array":
        return f"list of {_type(prop.get('items', {}), defs)}"
    if t == "object" and "properties" in prop:
        return prop.get("title", "object")
    rng = []
    if "minimum" in prop:
        rng.append(f"≥ {prop['minimum']:g}")
    if "maximum" in prop:
        rng.append(f"≤ {prop['maximum']:g}")
    fmt = {"string": "text", "integer": "integer", "number": "number", "boolean": "true/false", "null": "`null`"}.get(t, t)
    if prop.get("format") == "date":
        fmt = "date (YYYY-MM-DD)"
    return fmt + (f" ({', '.join(rng)})" if rng else "")


def fields(model_name: str) -> str:
    from backend import models as M

    model = getattr(M, model_name)
    schema = model.model_json_schema(by_alias=True)
    defs = schema.get("$defs", {})
    required = set(schema.get("required", []))
    rows = ["| Field | Type | Default | Notes |", "|---|---|---|---|"]
    for name, prop in schema["properties"].items():
        if name in required:
            default = "*required*"
        else:
            d = prop.get("default")
            if d is None:
                default = "`null`"
            elif isinstance(d, bool):
                default = f"`{str(d).lower()}`"
            elif isinstance(d, (list, dict)) and not d:
                default = "empty"
            else:
                default = f"`{d!r}`".replace("'", '"')
        note = prop.get("description", "").replace("|", "\\|")
        rows.append(f"| `{name}` | {_type(prop, defs)} | {default} | {note} |")
    return "\n".join(rows)


def cli() -> str:
    from backend import manage

    out = []

    def help_of(args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.suppress(SystemExit):
            manage.main(args)
        return buf.getvalue().replace("usage: python -m backend.manage", "usage: python -m backend.manage").strip()

    out.append("```text\n" + help_of(["--help"]) + "\n```")
    for cmd in ("list", "adduser", "passwd", "deluser"):
        out.append(f"### `{cmd}`\n\n```text\n{help_of([cmd, '--help'])}\n```")
    return "\n\n".join(out)


SINGULAR = {"domains": "domain", "groups": "group", "projects": "project", "milestones": "milestone",
            "references": "reference", "kinds": "kind", "states": "state", "reftypes": "reference type",
            "markers": "marker"}
SUMMARIES = {
    "get_workspace": "The whole workspace with derived data (supports `If-None-Match`).",
    "update_settings": "Change the settings (fork and merge line colours and widths).",
    "undo": "Revert the last change.",
    "get_version": "The running lineage version.",
    "backup": "Download a backup (`.tar.gz`).",
    "restore": "Replace the workspace with a backup sent as the body (`?force=true` across versions).",
    "login": "Log in: `{username, password}`; sets the session cookie.",
    "logout": "Log out: clears the session cookie.",
    "get_me": "The logged-in user.",
    "change_password": "Change your password: `{current, new}`; ends your other sessions.",
}


def summary(op_id: str) -> str:
    if op_id in SUMMARIES:
        return SUMMARIES[op_id]
    verb, _, t = op_id.partition("_")
    noun = SINGULAR.get(t, t)
    return {"create": f"Create a {noun}.", "update": f"Change fields of a {noun}.",
            "delete": f"Delete a {noun} (`?dry_run=true`: only report what would happen)."}.get(verb, "")


def api() -> str:
    os.environ.setdefault("LINEAGE_DEMO", "0")
    import logging

    logging.getLogger("lineage").setLevel(logging.ERROR)
    from backend.app import create_app

    with tempfile.TemporaryDirectory() as d:
        spec = create_app(d, frontend_dir=Path(d) / "none").openapi()
    public = {"/api/login", "/api/logout", "/api/version"}
    rows = ["| Method | Path | Login | Header | Summary |", "|---|---|---|---|---|"]
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            m = method.upper()
            login = "no" if path in public else "yes"
            header = "" if m in ("GET", "HEAD") else "`X-Lineage: 1`"
            rows.append(f"| {m} | `{path}` | {login} | {header} | {summary(op.get('operationId', ''))} |")
    return "\n".join(rows)


GENERATORS = {"fields": fields, "cli": cli, "api": api}


def on_page_markdown(markdown: str, page, config, files) -> str:
    def replace(m: re.Match) -> str:
        kind, arg = m.group(1), m.group(2)
        gen = GENERATORS.get(kind)
        if gen is None:
            raise ValueError(f"{page.file.src_path}: unknown generator {kind!r}")
        return gen(arg) if arg else gen()

    return MARKER.sub(replace, markdown)
