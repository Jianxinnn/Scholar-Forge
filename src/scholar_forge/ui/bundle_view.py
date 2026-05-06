from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from scholar_forge.bundle import BundlePaths, read_jsonl, read_yaml
from scholar_forge.models import EvidenceRecord, QueryRecord, ResourceRecord, SourceRecord, TriageRecord
from scholar_forge.ui.state import hydrate_run_meta
from scholar_forge.utils import to_plain_data


ARTIFACTS = {
    "brief": "brief.md",
    "references": "references.bib",
    "queries": "queries.jsonl",
    "sources": "sources.jsonl",
    "triage": "triage.jsonl",
    "evidence": "evidence.jsonl",
    "resources": "resources.jsonl",
    "provenance": "provenance.jsonl",
}


def render_brief_html(markdown_text: str) -> str:
    if not markdown_text:
        return '<p class="muted">No brief has been written yet.</p>'
    try:
        import bleach
        import markdown
    except ImportError:
        return f'<pre class="markdown-fallback">{escape(markdown_text)}</pre>'

    raw_html = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])
    allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS) | {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "pre",
        "code",
        "blockquote",
        "hr",
        "br",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
    allowed_attrs = {
        "a": ["href", "title"],
        "th": ["align"],
        "td": ["align"],
    }
    return bleach.clean(
        raw_html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


def _plain_records(records: list[Any]) -> list[dict[str, Any]]:
    return [to_plain_data(record) for record in records]


def _source_sort_key(source: dict[str, Any]) -> tuple[int, float, int, str]:
    decision_rank = {"include": 0, "maybe": 1, "exclude": 2}
    triage = source.get("triage") or {}
    decision = str(triage.get("decision", "maybe"))
    score = float(triage.get("total_score", 0.0) or 0.0)
    year = int(source.get("year") or 0)
    return (decision_rank.get(decision, 3), -score, -year, str(source.get("title", "")).lower())


def load_bundle_view(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    paths = BundlePaths(root)
    meta = hydrate_run_meta(root)
    request = read_yaml(paths.request)
    manifest = read_yaml(paths.manifest)
    queries = _plain_records(read_jsonl(paths.queries, QueryRecord))
    sources = _plain_records(read_jsonl(paths.sources, SourceRecord))
    triage = _plain_records(read_jsonl(paths.triage, TriageRecord))
    evidence = _plain_records(read_jsonl(paths.evidence, EvidenceRecord))
    resources = _plain_records(read_jsonl(paths.resources, ResourceRecord))
    provenance = read_jsonl(paths.provenance)
    brief = paths.brief.read_text(encoding="utf-8") if paths.brief.exists() else ""

    triage_by_source = {row["source_id"]: row for row in triage}
    evidence_by_source: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        evidence_by_source.setdefault(item["source_id"], []).append(item)

    for source in sources:
        source_id = source.get("source_id", "")
        source["triage"] = triage_by_source.get(source_id, {})
        source["evidence_count"] = len(evidence_by_source.get(source_id, []))
    sources.sort(key=_source_sort_key)

    artifacts = {name: (root / filename).exists() for name, filename in ARTIFACTS.items()}
    return {
        "root": str(root),
        "meta": meta.to_dict(),
        "request": request,
        "manifest": manifest,
        "queries": queries,
        "sources": sources,
        "triage": triage,
        "evidence": evidence,
        "resources": resources,
        "provenance": provenance,
        "brief": brief,
        "brief_html": render_brief_html(brief),
        "artifacts": artifacts,
        "counts": meta.counts,
    }


def read_artifact(run_dir: str | Path, name: str) -> tuple[str, str]:
    filename = ARTIFACTS.get(name)
    if not filename:
        raise ValueError(f"Unknown artifact: {name}")
    path = Path(run_dir) / filename
    if not path.exists():
        raise FileNotFoundError(path)
    if filename.endswith(".md"):
        media_type = "text/markdown; charset=utf-8"
    elif filename.endswith(".bib"):
        media_type = "text/plain; charset=utf-8"
    else:
        media_type = "application/jsonl; charset=utf-8"
    return path.read_text(encoding="utf-8"), media_type
