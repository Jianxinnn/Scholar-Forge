from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scholar_forge.bundle import BundlePaths, read_jsonl, read_yaml
from scholar_forge.utils import ensure_dir, to_plain_data, utc_now_iso, write_json


RUN_STATUSES = {"queued", "running", "done", "error", "cancel_requested", "cancelled"}
SLUG_RE = re.compile(r"[a-z0-9]+")


@dataclass(slots=True)
class RunMeta:
    run_id: str
    status: str
    stage: str
    created_at: str
    bundle_path: str
    completed_at: str = ""
    error: str = ""
    refined_from: str = ""
    question: str = ""
    profile: str = ""
    counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunMeta":
        status = str(data.get("status", "queued") or "queued")
        if status not in RUN_STATUSES:
            status = "queued"
        return cls(
            run_id=str(data.get("run_id", "") or ""),
            status=status,
            stage=str(data.get("stage", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            completed_at=str(data.get("completed_at", "") or ""),
            error=str(data.get("error", "") or ""),
            refined_from=str(data.get("refined_from", "") or ""),
            bundle_path=str(data.get("bundle_path", "") or ""),
            question=str(data.get("question", "") or ""),
            profile=str(data.get("profile", "") or ""),
            counts={str(k): int(v or 0) for k, v in dict(data.get("counts") or {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


def slugify_question(question: str, *, max_words: int = 8) -> str:
    words = SLUG_RE.findall(question.lower())
    slug = "-".join(words[:max_words])
    return slug[:80].strip("-") or "research"


def make_run_id(question: str, *, now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return f"{moment.strftime('%Y%m%d-%H%M%S')}-{slugify_question(question)}"


def unique_run_id(runs_dir: str | Path, question: str, *, now: datetime | None = None) -> str:
    root = Path(runs_dir)
    base = make_run_id(question, now=now)
    candidate = base
    index = 2
    while (root / candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def run_json_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / "run.json"


def read_run_meta(run_dir: str | Path) -> RunMeta | None:
    path = run_json_path(run_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return RunMeta.from_dict(data)


def write_run_meta(run_dir: str | Path, meta: RunMeta) -> None:
    write_json(run_json_path(run_dir), meta)


def create_run_meta(
    runs_dir: str | Path,
    *,
    question: str,
    profile: str = "",
    refined_from: str = "",
) -> RunMeta:
    root = ensure_dir(runs_dir)
    run_id = unique_run_id(root, question)
    run_dir = ensure_dir(root / run_id)
    meta = RunMeta(
        run_id=run_id,
        status="queued",
        stage="queued",
        created_at=utc_now_iso(),
        bundle_path=str(run_dir),
        question=question,
        profile=profile,
        refined_from=refined_from,
    )
    write_run_meta(run_dir, meta)
    return meta


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _triage_counts(path: Path) -> dict[str, int]:
    rows = read_jsonl(path)
    return {
        "include": sum(1 for row in rows if row.get("decision") == "include"),
        "maybe": sum(1 for row in rows if row.get("decision") == "maybe"),
        "exclude": sum(1 for row in rows if row.get("decision") == "exclude"),
    }


def hydrate_run_meta(run_dir: str | Path) -> RunMeta:
    run_path = Path(run_dir)
    meta = read_run_meta(run_path)
    paths = BundlePaths(run_path)
    manifest = read_yaml(paths.manifest)
    request = read_yaml(paths.request)

    if meta is None:
        meta = RunMeta(
            run_id=run_path.name,
            status="done" if paths.manifest.exists() else "error",
            stage="done" if paths.manifest.exists() else "unknown",
            created_at=str(manifest.get("created_at", "") or ""),
            completed_at=str((manifest.get("provenance") or {}).get("completed_at", "") or ""),
            bundle_path=str(run_path),
        )

    meta.question = meta.question or str(request.get("question", manifest.get("question", "")) or "")
    meta.profile = meta.profile or str(request.get("profile", manifest.get("profile", "")) or "")
    manifest_counts = dict(manifest.get("counts") or {})
    counts = {
        "queries": _jsonl_count(paths.queries),
        "sources": _jsonl_count(paths.sources),
        "triage": _jsonl_count(paths.triage),
        "evidence": _jsonl_count(paths.evidence),
        "resources": _jsonl_count(paths.resources),
    }
    counts.update({str(k): int(v or 0) for k, v in manifest_counts.items() if k not in counts or counts[k] == 0})
    counts.update(_triage_counts(paths.triage))
    meta.counts = counts
    if not meta.completed_at:
        meta.completed_at = str((manifest.get("provenance") or {}).get("completed_at", "") or "")
    manifest_completed_at = str((manifest.get("provenance") or {}).get("completed_at", "") or "")
    if paths.manifest.exists() and manifest_completed_at and meta.status in {"queued", "running", "cancel_requested"}:
        meta.status = "done"
        meta.stage = "done"
    return meta


def scan_runs(runs_dir: str | Path) -> list[RunMeta]:
    root = ensure_dir(runs_dir)
    runs: list[RunMeta] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if not (child / "run.json").exists() and not (child / "manifest.yaml").exists():
            continue
        runs.append(hydrate_run_meta(child))
    return sorted(runs, key=lambda item: item.created_at or item.run_id, reverse=True)
