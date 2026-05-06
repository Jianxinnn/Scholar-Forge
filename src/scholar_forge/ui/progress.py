from __future__ import annotations

from pathlib import Path
from typing import Any

from scholar_forge.bundle import BundlePaths, read_jsonl, read_yaml
from scholar_forge.ui.state import RunMeta


STEP_DEFS = [
    ("planning", "Planning"),
    ("searching", "Provider search"),
    ("dedupe", "Deduplication"),
    ("resources", "Resources"),
    ("ranking", "Ranking"),
    ("llm_triage", "LLM triage"),
    ("read_pdf", "PDF read"),
    ("evidence", "Evidence"),
    ("writing", "Bundle write"),
    ("brief", "Brief"),
    ("done", "Done"),
]

STAGE_ALIASES = {
    "queued": "planning",
    "starting": "planning",
    "planning": "planning",
    "planned": "planning",
    "search_result": "searching",
    "cancel_requested": "searching",
    "cancelled": "done",
    "interrupted": "done",
    "error": "done",
}


def _step_keys_for_request(request: dict[str, Any]) -> list[str]:
    keys = [key for key, _ in STEP_DEFS]
    if not request.get("llm_triage"):
        keys.remove("llm_triage")
    if not request.get("read_pdf"):
        keys.remove("read_pdf")
    return keys


def _normalize_stage(stage: str) -> str:
    return STAGE_ALIASES.get(stage, stage if stage in {key for key, _ in STEP_DEFS} else "planning")


def _artifact_status(paths: BundlePaths) -> dict[str, bool]:
    return {
        "request": paths.request.exists(),
        "queries": paths.queries.exists(),
        "sources": paths.sources.exists(),
        "triage": paths.triage.exists(),
        "evidence": paths.evidence.exists(),
        "resources": paths.resources.exists(),
        "brief": paths.brief.exists(),
        "references": paths.references.exists(),
        "manifest": paths.manifest.exists(),
    }


def _step_statuses(meta: RunMeta, request: dict[str, Any]) -> list[dict[str, str]]:
    keys = _step_keys_for_request(request)
    labels = dict(STEP_DEFS)
    current = _normalize_stage(meta.stage)
    if current not in keys:
        current = "done" if meta.status in {"done", "error", "cancelled"} else "planning"
    current_index = keys.index(current) if current in keys else 0
    rows = []
    for index, key in enumerate(keys):
        if meta.status == "done":
            state = "done"
        elif meta.status in {"error", "cancelled"}:
            if index < current_index:
                state = "done"
            elif index == current_index:
                state = meta.status
            else:
                state = "pending"
        elif index < current_index:
            state = "done"
        elif index == current_index:
            state = "active"
        else:
            state = "pending"
        rows.append({"key": key, "label": labels[key], "state": state})
    return rows


def _provider_events(provenance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for row in provenance:
        if not row.get("query") and row.get("provider") not in {"llm_triage", "llm_brief", "pdf_reader"}:
            continue
        provider = str(row.get("provider", "unknown") or "unknown")
        status = str(row.get("status", "unknown") or "unknown")
        detail = ""
        if row.get("error"):
            detail = str(row.get("error", ""))
        elif row.get("result_count") is not None:
            detail = f"{row.get('result_count')} results"
        elif row.get("reason"):
            detail = str(row.get("reason", ""))
        elif row.get("raw_file"):
            detail = str(row.get("raw_file", ""))
        events.append(
            {
                "timestamp": str(row.get("timestamp", "") or ""),
                "provider": provider,
                "query": str(row.get("query", "") or ""),
                "status": status,
                "detail": detail,
            }
        )
    return events


def _provider_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_provider: dict[str, dict[str, Any]] = {}
    for event in events:
        provider = str(event.get("provider", "unknown") or "unknown")
        item = by_provider.setdefault(
            provider,
            {"provider": provider, "queries": 0, "results": 0, "errors": 0, "last_status": ""},
        )
        if event.get("query"):
            item["queries"] += 1
        if event.get("status") == "error":
            item["errors"] += 1
        detail = str(event.get("detail", ""))
        if detail.endswith(" results"):
            try:
                item["results"] += int(detail.split(" ", 1)[0])
            except ValueError:
                pass
        item["last_status"] = event.get("status", "")
    return sorted(by_provider.values(), key=lambda item: item["provider"])


def build_progress_summary(run_dir: str | Path, meta: RunMeta) -> dict[str, Any]:
    root = Path(run_dir)
    paths = BundlePaths(root)
    request = read_yaml(paths.request)
    provenance = read_jsonl(paths.provenance)
    events = _provider_events(provenance)
    return {
        "run": meta.to_dict(),
        "steps": _step_statuses(meta, request),
        "providers": _provider_summary(events),
        "events": events[-20:],
        "artifacts": _artifact_status(paths),
    }
