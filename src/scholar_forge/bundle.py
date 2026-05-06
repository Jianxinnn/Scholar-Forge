from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TypeVar

import yaml

from .models import (
    BundleManifest,
    EvidenceRecord,
    QueryRecord,
    ResearchRequest,
    ResourceRecord,
    SourceRecord,
    TriageRecord,
)
from .utils import dumps_json, ensure_dir, safe_id, stable_hash, to_plain_data, utc_now_iso, write_json


T = TypeVar("T")
BUNDLE_FORMAT_VERSION = "1.1"
REQUIRED_BUNDLE_FILES = {
    "manifest": "manifest.yaml",
    "request": "request.yaml",
    "queries": "queries.jsonl",
    "sources": "sources.jsonl",
    "triage": "triage.jsonl",
    "evidence": "evidence.jsonl",
    "resources": "resources.jsonl",
    "brief": "brief.md",
    "references": "references.bib",
    "provenance": "provenance.jsonl",
}
JSONL_REQUIRED_FIELDS = {
    "queries": {"query", "intent", "provider_targets"},
    "sources": {"source_id", "title", "provider"},
    "triage": {"source_id", "decision", "total_score"},
    "evidence": {"evidence_id", "source_id", "claim", "evidence_text"},
    "resources": {"resource_id", "resource_kind", "source_ids", "status"},
}


@dataclass(slots=True)
class BundlePaths:
    root: Path

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.yaml"

    @property
    def request(self) -> Path:
        return self.root / "request.yaml"

    @property
    def queries(self) -> Path:
        return self.root / "queries.jsonl"

    @property
    def sources(self) -> Path:
        return self.root / "sources.jsonl"

    @property
    def triage(self) -> Path:
        return self.root / "triage.jsonl"

    @property
    def evidence(self) -> Path:
        return self.root / "evidence.jsonl"

    @property
    def resources(self) -> Path:
        return self.root / "resources.jsonl"

    @property
    def brief(self) -> Path:
        return self.root / "brief.md"

    @property
    def references(self) -> Path:
        return self.root / "references.bib"

    @property
    def provenance(self) -> Path:
        return self.root / "provenance.jsonl"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def notes(self) -> Path:
        return self.root / "notes"


def write_yaml(path: Path, value: Any) -> None:
    path.write_text(
        yaml.safe_dump(to_plain_data(value), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_jsonl(path: Path, records: Iterable[Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(dumps_json(record) + "\n")


def append_jsonl(path: Path, record: Any) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(dumps_json(record) + "\n")


def read_jsonl(path: Path, factory: type[T] | None = None) -> list[T] | list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[Any] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        records.append(factory.from_dict(data) if factory else data)
    return records


class BundleWriter:
    def __init__(self, root: str | Path):
        self.paths = BundlePaths(ensure_dir(root))
        ensure_dir(self.paths.raw)
        ensure_dir(self.paths.notes)

    @property
    def root(self) -> Path:
        return self.paths.root

    def write_request(self, request: ResearchRequest) -> None:
        write_yaml(self.paths.request, request)

    def write_queries(self, queries: list[QueryRecord]) -> None:
        write_jsonl(self.paths.queries, queries)

    def write_sources(self, sources: list[SourceRecord]) -> None:
        write_jsonl(self.paths.sources, sources)

    def write_triage(self, triage: list[TriageRecord]) -> None:
        write_jsonl(self.paths.triage, triage)

    def write_evidence(self, evidence: list[EvidenceRecord]) -> None:
        write_jsonl(self.paths.evidence, evidence)

    def write_resources(self, resources: list[ResourceRecord]) -> None:
        write_jsonl(self.paths.resources, resources)

    def write_brief(self, brief: str) -> None:
        self.paths.brief.write_text(brief, encoding="utf-8")

    def write_references(self, bibtex: str) -> None:
        self.paths.references.write_text(bibtex, encoding="utf-8")

    def write_note(self, source_id: str, content: str) -> None:
        path = self.paths.notes / f"{source_id}.md"
        path.write_text(content, encoding="utf-8")

    def append_provenance(self, record: dict[str, Any]) -> None:
        append_jsonl(self.paths.provenance, record)

    def raw_path(self, provider: str, key: str) -> Path:
        folder = ensure_dir(self.paths.raw / provider)
        return folder / f"{stable_hash(key, 24)}.json"

    def write_raw(self, provider: str, key: str, raw: Any) -> Path:
        path = self.raw_path(provider, key)
        write_json(path, raw)
        return path

    def write_manifest(
        self,
        request: ResearchRequest,
        *,
        queries: int = 0,
        sources: int = 0,
        triage: int = 0,
        evidence: int = 0,
        resources: int = 0,
        extra: dict[str, Any] | None = None,
    ) -> BundleManifest:
        manifest = BundleManifest(
            bundle_id=safe_id("bundle", request.question, request.profile),
            bundle_format_version=BUNDLE_FORMAT_VERSION,
            created_at=utc_now_iso(),
            question=request.question,
            profile=request.profile,
            counts={
                "queries": queries,
                "sources": sources,
                "triage": triage,
                "evidence": evidence,
                "resources": resources,
            },
            files=REQUIRED_BUNDLE_FILES.copy(),
            provenance=extra or {},
        )
        write_yaml(self.paths.manifest, manifest)
        return manifest


def load_request(path: str | Path) -> ResearchRequest:
    p = Path(path)
    if p.is_dir():
        p = p / "request.yaml"
    return ResearchRequest.from_dict(read_yaml(p))


def inspect_bundle(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    paths = BundlePaths(root)
    manifest = read_yaml(paths.manifest)
    request = read_yaml(paths.request)
    queries = read_jsonl(paths.queries)
    sources = read_jsonl(paths.sources)
    triage = read_jsonl(paths.triage)
    evidence = read_jsonl(paths.evidence)
    resources = read_jsonl(paths.resources)
    include_count = sum(1 for row in triage if row.get("decision") == "include")
    maybe_count = sum(1 for row in triage if row.get("decision") == "maybe")
    exclude_count = sum(1 for row in triage if row.get("decision") == "exclude")
    validation_errors = validate_bundle(root)
    return {
        "root": str(root),
        "manifest": manifest,
        "question": request.get("question", manifest.get("question", "")),
        "profile": request.get("profile", manifest.get("profile", "general")),
        "counts": {
            "queries": len(queries),
            "sources": len(sources),
            "triage": len(triage),
            "include": include_count,
            "maybe": maybe_count,
            "exclude": exclude_count,
            "evidence": len(evidence),
            "resources": len(resources),
        },
        "files": {
            "manifest": paths.manifest.exists(),
            "request": paths.request.exists(),
            "queries": paths.queries.exists(),
            "sources": paths.sources.exists(),
            "triage": paths.triage.exists(),
            "evidence": paths.evidence.exists(),
            "resources": paths.resources.exists(),
            "brief": paths.brief.exists(),
            "references": paths.references.exists(),
            "provenance": paths.provenance.exists(),
        },
        "validation_errors": validation_errors,
    }


def validate_bundle(path: str | Path) -> list[str]:
    root = Path(path)
    paths = BundlePaths(root)
    errors: list[str] = []
    manifest = read_yaml(paths.manifest)
    request = read_yaml(paths.request)

    if paths.manifest.exists():
        version = manifest.get("bundle_format_version")
        if version != BUNDLE_FORMAT_VERSION:
            errors.append(f"manifest.yaml bundle_format_version must be {BUNDLE_FORMAT_VERSION}")
        files = manifest.get("files") or {}
        for key, filename in REQUIRED_BUNDLE_FILES.items():
            if files.get(key) != filename:
                errors.append(f"manifest.yaml files.{key} must be {filename}")

    if paths.request.exists() and not request.get("question"):
        errors.append("request.yaml question is required")

    jsonl_paths = {
        "queries": paths.queries,
        "sources": paths.sources,
        "triage": paths.triage,
        "evidence": paths.evidence,
        "resources": paths.resources,
    }
    for name, jsonl_path in jsonl_paths.items():
        if not jsonl_path.exists():
            continue
        required = JSONL_REQUIRED_FIELDS[name]
        for line_no, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"{jsonl_path.name}:{line_no} must be valid JSON")
                continue
            if not isinstance(data, dict):
                errors.append(f"{jsonl_path.name}:{line_no} must be a JSON object")
                continue
            missing = sorted(required - set(data))
            if missing:
                errors.append(f"{jsonl_path.name}:{line_no} missing fields: {', '.join(missing)}")
    return errors
