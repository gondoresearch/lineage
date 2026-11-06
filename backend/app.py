"""HTTP routes. Run with: uvicorn --factory backend.app:create_app"""

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import graph
from . import models as M
from .store import BadBackup, Broken, NothingToUndo, Store, VersionMismatch, app_version

ERR = {"model": M.ErrorOut}

ENTITY_MODELS = {
    "domains": (M.DomainCreate, M.DomainPatch, M.Domain),
    "groups": (M.GroupCreate, M.GroupPatch, M.Group),
    "projects": (M.ProjectCreate, M.ProjectPatch, M.Project),
    "milestones": (M.MilestoneCreate, M.MilestonePatch, M.Milestone),
    "references": (M.ReferenceCreate, M.ReferencePatch, M.Reference),
    "kinds": (M.KindCreate, M.KindPatch, M.Kind),
    "states": (M.StateCreate, M.StatePatch, M.State),
    "reftypes": (M.RefTypeCreate, M.RefTypePatch, M.RefType),
    "markers": (M.MarkerCreate, M.MarkerPatch, M.Marker),
}


def _errors(status: int, errors: list[str]) -> JSONResponse:
    return JSONResponse({"errors": errors}, status_code=status)


def create_app(data_dir: str | Path | None = None, frontend_dir: str | Path | None = None) -> FastAPI:
    store = Store(Path(data_dir or os.environ.get("DATA_DIR", "/data")))
    app = FastAPI(title="lineage", version="0.1.0")
    app.state.store = store

    @app.exception_handler(RequestValidationError)
    def _(request, exc: RequestValidationError):
        msgs = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err["loc"] if x != "body")
            msgs.append(f"{loc}: {err['msg']}" if loc else err["msg"])
        return _errors(422, msgs)

    @app.exception_handler(graph.Invalid)
    def _(request, exc: graph.Invalid):
        return _errors(422, exc.errors)

    @app.exception_handler(graph.NotFound)
    def _(request, exc: graph.NotFound):
        return _errors(404, [str(exc)])

    @app.exception_handler(graph.Blocked)
    def _(request, exc: graph.Blocked):
        return JSONResponse({"blockers": exc.blockers}, status_code=409)

    @app.exception_handler(Broken)
    def _(request, exc: Broken):
        return _errors(500, ["The data folder is not a valid workspace:", *exc.errors])

    @app.exception_handler(BadBackup)
    def _(request, exc: BadBackup):
        return _errors(422, exc.errors)

    @app.exception_handler(VersionMismatch)
    def _(request, exc: VersionMismatch):
        return JSONResponse(
            {
                "errors": [
                    f"This backup was made by lineage {exc.backup}; this is lineage {exc.current}. "
                    "Restore it anyway only if you are sure the formats are compatible."
                ],
                "backup_version": exc.backup,
                "current_version": exc.current,
            },
            status_code=409,
        )

    @app.exception_handler(NothingToUndo)
    def _(request, exc: NothingToUndo):
        return _errors(409, ["Nothing to undo."])

    @app.get(
        "/api/workspace",
        response_model=M.WorkspaceOut,
        responses={304: {"description": "Not modified"}, 500: ERR},
        operation_id="get_workspace",
    )
    def get_workspace(request: Request):
        ws = store.read()
        out = M.WorkspaceOut(**dict(ws), derived=graph.derive(ws))
        body = out.model_dump_json().encode()
        etag = '"' + hashlib.sha1(body).hexdigest() + '"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return Response(body, media_type="application/json", headers={"ETag": etag})

    def register(t: str, Create, Patch, Entity):
        @app.post(
            f"/api/{t}",
            response_model=Entity,
            status_code=201,
            operation_id=f"create_{t}",
            responses={422: ERR, 500: ERR},
            tags=[t],
        )
        def create(body: Create):
            return store.mutate(lambda ws: graph.create(ws, t, body))

        @app.patch(
            f"/api/{t}/{{id}}",
            response_model=Entity,
            operation_id=f"update_{t}",
            responses={404: ERR, 422: ERR, 500: ERR},
            tags=[t],
        )
        def update(id: str, body: Patch):
            data = body.model_dump(by_alias=True, exclude_unset=True)
            return store.mutate(lambda ws: graph.patch(ws, t, id, data))

        @app.delete(
            f"/api/{t}/{{id}}",
            status_code=204,
            response_model=None,
            operation_id=f"delete_{t}",
            responses={
                200: {"model": M.DryRunOut, "description": "Dry run: what would happen"},
                404: ERR,
                409: {"model": M.BlockedOut},
                422: ERR,
                500: ERR,
            },
            tags=[t],
        )
        def delete(id: str, dry_run: bool = False):
            if dry_run:
                removes, blockers = graph.delete_plan(store.read(), t, id)
                return JSONResponse({"removes": removes, "blockers": blockers})
            store.mutate(lambda ws: graph.delete(ws, t, id))
            return Response(status_code=204)

    for t, (Create, Patch, Entity) in ENTITY_MODELS.items():
        register(t, Create, Patch, Entity)

    @app.patch(
        "/api/settings",
        response_model=M.Settings,
        operation_id="update_settings",
        responses={422: ERR, 500: ERR},
    )
    def update_settings(body: M.SettingsPatch):
        data = body.model_dump(exclude_unset=True)

        def fn(ws: M.Workspace):
            ws.settings = M.Settings.model_validate({**ws.settings.model_dump(), **data})
            return ws.settings

        return store.mutate(fn)

    @app.get("/api/version", response_model=M.VersionOut, operation_id="get_version")
    def version():
        return {"version": app_version()}

    @app.get(
        "/api/backup",
        operation_id="backup",
        response_class=Response,
        responses={200: {"content": {"application/gzip": {"schema": {"type": "string", "format": "binary"}}},
                         "description": "A .tar.gz of the whole data folder, with a manifest recording the version."}},
    )
    def backup():
        data, manifest = store.backup()
        stamp = manifest["created"].replace("-", "").replace(":", "").replace("T", "-")[:15]
        name = f"lineage-backup-{manifest['version']}-{stamp}.tar.gz"
        return Response(data, media_type="application/gzip", headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.post(
        "/api/restore",
        response_model=M.RestoreOut,
        operation_id="restore",
        responses={409: {"model": M.VersionMismatchOut, "description": "Made by another version; resend with force=true"}, 422: ERR},
        openapi_extra={"requestBody": {"required": True, "content": {"application/gzip": {"schema": {"type": "string", "format": "binary"}}}}},
    )
    async def restore(request: Request, force: bool = False):
        """Replace the whole workspace with a backup (.tar.gz from /api/backup, sent as the request body).
        The current data is snapshotted first, so /api/undo reverts the restore."""
        data = await request.body()
        manifest = await run_in_threadpool(store.restore, data, force)
        return {"restored_version": manifest["version"], "created": manifest.get("created"), "current_version": app_version()}

    @app.post("/api/undo", status_code=204, operation_id="undo", responses={409: ERR})
    def undo():
        store.undo()
        return Response(status_code=204)

    fdir = Path(frontend_dir or os.environ.get("FRONTEND_DIR", Path(__file__).parent.parent / "frontend" / "dist"))
    if fdir.is_dir():
        app.mount("/", StaticFiles(directory=fdir, html=True), name="frontend")

    return app
