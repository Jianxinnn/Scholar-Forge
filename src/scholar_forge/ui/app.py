from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scholar_forge.config import load_config
from scholar_forge.ui.bundle_view import load_bundle_view, read_artifact
from scholar_forge.ui.followup import answer_followup
from scholar_forge.ui.jobs import JobManager, provider_statuses
from scholar_forge.ui.progress import build_progress_summary


def _ui_resource_path(name: str) -> str:
    return str(files("scholar_forge.ui").joinpath(name))


def create_app(*, runs_dir: str | Path = "./scholar-runs", config_path: str | Path | None = None) -> FastAPI:
    templates = Jinja2Templates(directory=_ui_resource_path("templates"))
    manager = JobManager(runs_dir, config_path=config_path)
    app = FastAPI(title="ScholarForge Local UI")
    app.state.manager = manager
    app.state.config_path = config_path
    app.mount("/static", StaticFiles(directory=_ui_resource_path("static")), name="static")

    def defaults() -> dict[str, Any]:
        config = load_config(config_path)
        return {
            "max_papers": config.default_max_papers(),
            "domain": config.default_domain(),
            "language": config.default_language(),
            "providers": config.default_providers("general"),
        }

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "runs": [run.to_dict() for run in manager.list_runs()],
                "defaults": defaults(),
                "providers": provider_statuses(config_path),
            },
        )

    @app.post("/api/runs")
    async def create_run(request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            meta = manager.start_run(payload)
            return JSONResponse(meta.to_dict())
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/runs")
    async def list_runs():
        return {"runs": [run.to_dict() for run in manager.list_runs()]}

    @app.get("/runs/{run_id}")
    async def run_page(request: Request, run_id: str):
        run_dir = manager.runs_dir / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        bundle = load_bundle_view(run_dir)
        return templates.TemplateResponse(
            request,
            "run.html",
            {
                "request": request,
                "run_id": run_id,
                "bundle": bundle,
            },
        )

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        try:
            meta = manager.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        return {"run": meta.to_dict()}

    @app.get("/api/runs/{run_id}/bundle")
    async def get_bundle(run_id: str):
        run_dir = manager.runs_dir / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        return load_bundle_view(run_dir)

    @app.get("/api/runs/{run_id}/progress")
    async def get_progress(run_id: str):
        run_dir = manager.runs_dir / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        try:
            meta = manager.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        return build_progress_summary(run_dir, meta)

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel_run(run_id: str):
        try:
            meta = manager.request_cancel(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        return {"run": meta.to_dict()}

    @app.post("/api/runs/{run_id}/followup")
    async def followup(run_id: str, request: Request):
        run_dir = manager.runs_dir / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object")
        bundle = load_bundle_view(run_dir)
        answer = answer_followup(
            bundle,
            question=str(payload.get("question", "") or ""),
            intent=str(payload.get("intent", "") or ""),
            source_id=str(payload.get("source_id", "") or ""),
            config=load_config(config_path),
        )
        return answer

    @app.get("/artifacts/{run_id}/{name}")
    async def artifact(run_id: str, name: str):
        run_dir = manager.runs_dir / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        try:
            text, media_type = read_artifact(run_dir, name)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return PlainTextResponse(text, media_type=media_type)

    return app


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    runs_dir: str | Path = "./scholar-runs",
    config_path: str | Path | None = None,
) -> int:
    import uvicorn

    app = create_app(runs_dir=runs_dir, config_path=config_path)
    print(f"ScholarForge UI: http://{host}:{port}")
    print(f"Runs dir: {Path(runs_dir).resolve()}")
    uvicorn.run(app, host=host, port=port)
    return 0
