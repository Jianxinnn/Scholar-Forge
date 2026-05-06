from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from scholar_forge.config import load_config
from scholar_forge.models import ResearchRequest
from scholar_forge.pipeline import PipelineCancelled, ScholarPipeline
from scholar_forge.ui.state import RunMeta, create_run_meta, hydrate_run_meta, scan_runs, write_run_meta
from scholar_forge.utils import ensure_dir, utc_now_iso


ACTIVE_STATUSES = {"queued", "running", "cancel_requested"}


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _providers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _max_papers(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def request_from_payload(payload: dict[str, Any]) -> ResearchRequest:
    question = str(payload.get("question", "") or "").strip()
    if not question:
        raise ValueError("question is required")
    return ResearchRequest(
        question=question,
        domain=str(payload.get("domain", "") or ""),
        profile=str(payload.get("profile", "") or ""),
        year_range=str(payload.get("year_range", payload.get("year", "")) or ""),
        max_papers=_max_papers(payload.get("max_papers")),
        providers=_providers(payload.get("providers")),
        language=str(payload.get("language", "") or ""),
        read_pdf=_bool_value(payload.get("read_pdf")),
        use_llm=_bool_value(payload.get("use_llm"), default=True),
        llm_triage=_bool_value(payload.get("llm_triage")),
    )


class JobManager:
    def __init__(self, runs_dir: str | Path, *, config_path: str | Path | None = None):
        self.runs_dir = ensure_dir(runs_dir)
        self.config_path = config_path
        self._lock = threading.Lock()
        self._active_run_id: str = ""
        self._active_thread: threading.Thread | None = None
        self._cancel_events: dict[str, threading.Event] = {}

    def _run_dir(self, run_id: str) -> Path:
        if "/" in run_id or "\\" in run_id or run_id.startswith("."):
            raise KeyError(f"Invalid run id: {run_id}")
        return self.runs_dir / run_id

    def _hydrate_managed(self, run_dir: Path) -> RunMeta:
        meta = hydrate_run_meta(run_dir)
        if meta.status in ACTIVE_STATUSES and meta.run_id != self._active_run_id:
            meta.status = "error"
            meta.stage = "interrupted"
            meta.completed_at = meta.completed_at or utc_now_iso()
            meta.error = meta.error or "Run was interrupted because the UI server stopped before completion."
            write_run_meta(run_dir, meta)
        return meta

    def list_runs(self) -> list[RunMeta]:
        runs = scan_runs(self.runs_dir)
        return [self._hydrate_managed(self._run_dir(run.run_id)) for run in runs]

    def get_run(self, run_id: str) -> RunMeta:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise KeyError(run_id)
        return self._hydrate_managed(run_dir)

    def _active_running(self) -> bool:
        thread = self._active_thread
        if not self._active_run_id or thread is None:
            return False
        if thread.is_alive():
            return True
        self._active_run_id = ""
        self._active_thread = None
        return False

    def start_run(self, payload: dict[str, Any]) -> RunMeta:
        request = request_from_payload(payload)
        with self._lock:
            if self._active_running():
                raise RuntimeError("Another run is already active.")
            meta = create_run_meta(
                self.runs_dir,
                question=request.question,
                profile=request.profile,
                refined_from=str(payload.get("refined_from", "") or ""),
            )
            cancel_event = threading.Event()
            self._cancel_events[meta.run_id] = cancel_event
            thread = threading.Thread(
                target=self._run_pipeline,
                args=(meta.run_id, request, _bool_value(payload.get("refresh")), cancel_event),
                daemon=True,
            )
            self._active_run_id = meta.run_id
            self._active_thread = thread
            thread.start()
            return meta

    def request_cancel(self, run_id: str) -> RunMeta:
        with self._lock:
            event = self._cancel_events.get(run_id)
            if event:
                event.set()
            meta = self.get_run(run_id)
            if meta.status in ACTIVE_STATUSES:
                meta.status = "cancel_requested"
                meta.stage = meta.stage or "cancel_requested"
                write_run_meta(self._run_dir(run_id), meta)
            return meta

    def _update_run(self, run_id: str, **changes: Any) -> RunMeta:
        with self._lock:
            run_dir = self._run_dir(run_id)
            meta = hydrate_run_meta(run_dir)
            for key, value in changes.items():
                setattr(meta, key, value)
            write_run_meta(run_dir, meta)
            return meta

    def _run_pipeline(
        self,
        run_id: str,
        request: ResearchRequest,
        refresh: bool,
        cancel_event: threading.Event,
    ) -> None:
        run_dir = self._run_dir(run_id)

        def progress(stage: str, detail: dict[str, Any]) -> None:
            status = "cancel_requested" if cancel_event.is_set() else "running"
            self._update_run(run_id, status=status, stage=stage)

        try:
            self._update_run(run_id, status="running", stage="starting")
            pipeline = ScholarPipeline.from_config(self.config_path)
            pipeline.run(
                request,
                out=run_dir,
                refresh=refresh,
                progress=progress,
                should_cancel=cancel_event.is_set,
            )
            self._update_run(run_id, status="done", stage="done", completed_at=utc_now_iso(), error="")
        except PipelineCancelled as exc:
            self._update_run(
                run_id,
                status="cancelled",
                stage="cancelled",
                completed_at=utc_now_iso(),
                error=str(exc),
            )
        except Exception as exc:
            self._update_run(
                run_id,
                status="error",
                stage="error",
                completed_at=utc_now_iso(),
                error=str(exc),
            )
        finally:
            with self._lock:
                if self._active_run_id == run_id:
                    self._active_run_id = ""
                    self._active_thread = None
                self._cancel_events.pop(run_id, None)


def provider_statuses(config_path: str | Path | None = None) -> list[dict[str, Any]]:
    from scholar_forge.providers import provider_registry

    config = load_config(config_path)
    rows = []
    for name, provider in provider_registry().items():
        status = provider.status(config)
        rows.append(
            {
                "name": name,
                "enabled": status.enabled,
                "available": status.available,
                "detail": status.detail,
            }
        )
    return rows
