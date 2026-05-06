from __future__ import annotations

from .models import EvidenceRecord, ResearchRequest, SourceRecord, TriageRecord
from .utils import safe_id


def _best_text(source: SourceRecord) -> tuple[str, str]:
    pdf_text = source.raw.get("pdf_text_preview")
    if isinstance(pdf_text, str) and pdf_text.strip():
        return pdf_text.strip(), "pdf_section"
    if source.abstract:
        return source.abstract, "abstract"
    if source.snippet:
        return source.snippet, "snippet"
    tldr = source.raw.get("tldr")
    if isinstance(tldr, str) and tldr:
        return tldr, "tldr"
    return source.title, "title"


def extract_evidence(
    request: ResearchRequest,
    sources: list[SourceRecord],
    triage: list[TriageRecord],
) -> list[EvidenceRecord]:
    included = {t.source_id for t in triage if t.decision == "include"}
    records: list[EvidenceRecord] = []
    for source in sources:
        if source.source_id not in included:
            continue
        text, kind = _best_text(source)
        if not text:
            continue
        claim = f"{source.title} provides context for: {request.question}" if source.title else f"Context for: {request.question}"
        records.append(
            EvidenceRecord(
                evidence_id=safe_id("ev", source.source_id, kind, text[:120]),
                source_id=source.source_id,
                claim=claim,
                evidence_text=text[:1200],
                evidence_kind=kind,
                supports_or_contradicts="context",
                confidence=0.6 if kind in {"abstract", "tldr"} else 0.45,
                source_locator=source.url or source.pdf_url,
            )
        )
    return records


def note_for_source(source: SourceRecord, evidence: list[EvidenceRecord]) -> str:
    lines = [f"# {source.title}", ""]
    if source.authors:
        lines.append(f"Authors: {', '.join(source.authors[:8])}")
    if source.year:
        lines.append(f"Year: {source.year}")
    if source.venue:
        lines.append(f"Venue: {source.venue}")
    if source.doi:
        lines.append(f"DOI: {source.doi}")
    if source.url:
        lines.append(f"URL: {source.url}")
    if source.pdf_url:
        lines.append(f"PDF: {source.pdf_url}")
    lines.append("")
    if source.abstract:
        lines.extend(["## Abstract", "", source.abstract, ""])
    source_evidence = [e for e in evidence if e.source_id == source.source_id]
    if source_evidence:
        lines.extend(["## Evidence", ""])
        for item in source_evidence:
            lines.append(f"- {item.evidence_text[:500]}")
    return "\n".join(lines).strip() + "\n"
