from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Decision = Literal["include", "maybe", "exclude"]
EvidenceDirection = Literal["supports", "contradicts", "context"]


@dataclass(slots=True)
class ResearchRequest:
    question: str
    domain: str = ""
    profile: str = ""
    year_range: str = ""
    max_papers: int | None = None
    providers: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    language: str = ""
    read_pdf: bool = False
    use_llm: bool = True
    llm_triage: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchRequest":
        max_papers = data.get("max_papers")
        return cls(
            question=str(data.get("question", "")),
            domain=str(data.get("domain", "") or ""),
            profile=str(data.get("profile", data.get("domain", "")) or ""),
            year_range=str(data.get("year_range", data.get("year", "")) or ""),
            max_papers=int(max_papers) if max_papers not in (None, "") else None,
            providers=list(data.get("providers") or []),
            constraints=dict(data.get("constraints") or {}),
            language=str(data.get("language", "") or ""),
            read_pdf=bool(data.get("read_pdf", False)),
            use_llm=bool(data.get("use_llm", True)),
            llm_triage=bool(data.get("llm_triage", False)),
        )


@dataclass(slots=True)
class QueryRecord:
    query: str
    intent: str = "discovery"
    provider_targets: list[str] = field(default_factory=list)
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryRecord":
        return cls(
            query=str(data.get("query", "")),
            intent=str(data.get("intent", "discovery") or "discovery"),
            provider_targets=list(data.get("provider_targets") or []),
            rationale=str(data.get("rationale", "") or ""),
        )


@dataclass(slots=True)
class SourceRecord:
    source_id: str
    title: str
    source_type: str = "paper"
    abstract: str = ""
    snippet: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    semantic_scholar_id: str = ""
    openalex_id: str = ""
    url: str = ""
    pdf_url: str = ""
    provider: str = ""
    citation_count: int | None = None
    fields: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRecord":
        return cls(
            source_id=str(data.get("source_id", "")),
            title=str(data.get("title", "")),
            source_type=str(data.get("source_type", "paper") or "paper"),
            abstract=str(data.get("abstract", "") or ""),
            snippet=str(data.get("snippet", "") or ""),
            authors=list(data.get("authors") or []),
            year=data.get("year"),
            venue=str(data.get("venue", "") or ""),
            doi=str(data.get("doi", "") or ""),
            arxiv_id=str(data.get("arxiv_id", "") or ""),
            pubmed_id=str(data.get("pubmed_id", "") or ""),
            semantic_scholar_id=str(data.get("semantic_scholar_id", "") or ""),
            openalex_id=str(data.get("openalex_id", "") or ""),
            url=str(data.get("url", "") or ""),
            pdf_url=str(data.get("pdf_url", "") or ""),
            provider=str(data.get("provider", "") or ""),
            citation_count=data.get("citation_count"),
            fields=list(data.get("fields") or []),
            raw=dict(data.get("raw") or {}),
        )


@dataclass(slots=True)
class TriageRecord:
    source_id: str
    relevance_score: float
    evidence_score: float
    novelty_score: float
    total_score: float
    decision: Decision
    reason: str = ""
    llm_score: float | None = None
    llm_reason: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriageRecord":
        return cls(
            source_id=str(data.get("source_id", "")),
            relevance_score=float(data.get("relevance_score", 0.0) or 0.0),
            evidence_score=float(data.get("evidence_score", 0.0) or 0.0),
            novelty_score=float(data.get("novelty_score", 0.0) or 0.0),
            total_score=float(data.get("total_score", 0.0) or 0.0),
            decision=data.get("decision", "maybe"),
            reason=str(data.get("reason", "") or ""),
            llm_score=data.get("llm_score"),
            llm_reason=str(data.get("llm_reason", "") or ""),
        )


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    source_id: str
    claim: str
    evidence_text: str
    evidence_kind: str = "abstract"
    supports_or_contradicts: EvidenceDirection = "context"
    confidence: float = 0.5
    source_locator: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        return cls(
            evidence_id=str(data.get("evidence_id", "")),
            source_id=str(data.get("source_id", "")),
            claim=str(data.get("claim", "") or ""),
            evidence_text=str(data.get("evidence_text", "") or ""),
            evidence_kind=str(data.get("evidence_kind", "abstract") or "abstract"),
            supports_or_contradicts=data.get("supports_or_contradicts", "context"),
            confidence=float(data.get("confidence", 0.5) or 0.5),
            source_locator=str(data.get("source_locator", "") or ""),
        )


@dataclass(slots=True)
class ResourceRecord:
    resource_id: str
    resource_kind: str
    source_ids: list[str] = field(default_factory=list)
    title: str = ""
    url: str = ""
    identifiers: dict[str, list[str]] = field(default_factory=dict)
    access: list[dict[str, str]] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    status: str = "candidate"
    confidence: float = 0.5
    reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResourceRecord":
        return cls(
            resource_id=str(data.get("resource_id", "")),
            resource_kind=str(data.get("resource_kind", "") or ""),
            source_ids=list(data.get("source_ids") or []),
            title=str(data.get("title", "") or ""),
            url=str(data.get("url", "") or ""),
            identifiers={str(k): list(v or []) for k, v in dict(data.get("identifiers") or {}).items()},
            access=[dict(item) for item in list(data.get("access") or []) if isinstance(item, dict)],
            providers=list(data.get("providers") or []),
            status=str(data.get("status", "candidate") or "candidate"),
            confidence=float(data.get("confidence", 0.5) or 0.5),
            reason=str(data.get("reason", "") or ""),
            raw=dict(data.get("raw") or {}),
        )


@dataclass(slots=True)
class BundleManifest:
    bundle_id: str
    bundle_format_version: str
    created_at: str
    question: str
    profile: str
    counts: dict[str, int] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BundleManifest":
        return cls(
            bundle_id=str(data.get("bundle_id", "")),
            bundle_format_version=str(data.get("bundle_format_version", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            question=str(data.get("question", "") or ""),
            profile=str(data.get("profile", "general") or "general"),
            counts=dict(data.get("counts") or {}),
            files=dict(data.get("files") or {}),
            provenance=dict(data.get("provenance") or {}),
        )
