from __future__ import annotations

from .models import ResearchRequest, SourceRecord, TriageRecord
from .utils import tokenize


BIOMOL_FIELDS = {"biology", "medicine", "chemistry", "biochemistry", "genetics"}
INCLUDE_SCORE_THRESHOLD = 0.4
MAYBE_SCORE_THRESHOLD = 0.25
AGENT_REQUIRED_TERMS = {
    "agent",
    "agents",
    "agentic",
    "llm",
    "llms",
    "language model",
    "large language model",
    "mcp",
    "model context protocol",
    "skill.md",
}
AGENT_SKILL_TERMS = {
    "skill",
    "skills",
    "skill library",
    "skill acquisition",
    "self improving",
    "self-improving",
    "self evolving",
    "self-evolving",
    "self improvement",
    "self-improvement",
    "lifelong learning",
    "reflection",
    "experience",
    "tool use",
    "tool-grounded",
}
AGENT_OFFTOPIC_TERMS = {
    "student",
    "students",
    "dyscalculia",
    "education",
    "educational",
    "teaching",
    "interpreter training",
    "interpreter",
    "speech repository",
    "education framework",
    "teaching and learning",
    "speaking skills",
    "self-directed learning",
    "customizable learning experiences",
}


def _keyword_score(request: ResearchRequest, source: SourceRecord) -> float:
    query_tokens = tokenize(request.question)
    if not query_tokens:
        return 0.0
    title_tokens = tokenize(source.title)
    body_tokens = tokenize(" ".join([source.abstract, source.snippet]))
    title_overlap = len(query_tokens & title_tokens) / len(query_tokens)
    body_overlap = len(query_tokens & body_tokens) / len(query_tokens)
    return min(1.0, title_overlap * 0.7 + body_overlap * 0.3)


def _evidence_score(source: SourceRecord) -> float:
    score = 0.0
    if source.abstract:
        score += 0.35
    if source.snippet:
        score += 0.15
    if source.pdf_url:
        score += 0.2
    if source.doi or source.arxiv_id or source.pubmed_id:
        score += 0.15
    if source.raw.get("providers_seen") and len(source.raw["providers_seen"]) > 1:
        score += 0.15
    return min(1.0, score)


def _novelty_score(source: SourceRecord) -> float:
    if not source.year:
        return 0.2
    if source.year >= 2024:
        return 1.0
    if source.year >= 2020:
        return 0.75
    if source.year >= 2015:
        return 0.45
    return 0.2


def _impact_score(source: SourceRecord) -> float:
    citations = source.citation_count or 0
    return min(1.0, citations / 500.0)


def _domain_boost(request: ResearchRequest, source: SourceRecord) -> float:
    if request.profile != "biomol" and request.domain != "biomol":
        return 0.0
    fields = {f.lower() for f in source.fields}
    if source.provider == "pubmed" or fields & BIOMOL_FIELDS:
        return 0.1
    return 0.0


def _text_blob(source: SourceRecord) -> str:
    return " ".join([source.title, source.abstract, source.snippet, " ".join(source.fields)]).lower()


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _agent_skills_match(source: SourceRecord) -> bool:
    text = _text_blob(source)
    return _contains_any(text, AGENT_REQUIRED_TERMS) and _contains_any(text, AGENT_SKILL_TERMS)


def _profile_adjustment(request: ResearchRequest, source: SourceRecord) -> float:
    if request.profile != "agent_skills":
        return 0.0
    text = _text_blob(source)
    if _contains_any(text, AGENT_OFFTOPIC_TERMS):
        return -0.45
    if _agent_skills_match(source):
        return 0.12
    return -0.12


def rank_sources(request: ResearchRequest, sources: list[SourceRecord]) -> list[TriageRecord]:
    scored: list[tuple[SourceRecord, TriageRecord]] = []
    for source in sources:
        relevance = _keyword_score(request, source)
        evidence = _evidence_score(source)
        novelty = _novelty_score(source)
        impact = _impact_score(source)
        total = min(
            1.0,
            relevance * 0.45
            + evidence * 0.25
            + novelty * 0.15
            + impact * 0.10
            + _domain_boost(request, source)
            + _profile_adjustment(request, source),
        )
        total = max(0.0, total)
        reason = (
            "Deterministic score from keyword overlap, evidence availability, recency, impact, "
            "and domain/profile adjustments."
        )
        scored.append(
            (
                source,
                TriageRecord(
                    source_id=source.source_id,
                    relevance_score=round(relevance, 4),
                    evidence_score=round(evidence, 4),
                    novelty_score=round(novelty, 4),
                    total_score=round(total, 4),
                    decision="maybe",
                    reason=reason,
                ),
            )
        )

    scored.sort(key=lambda item: item[1].total_score, reverse=True)
    include_cutoff = max(1, request.max_papers or 1)
    maybe_cutoff = include_cutoff * 2

    ranked: list[TriageRecord] = []
    included_count = 0
    maybe_count = 0
    for index, (_, triage) in enumerate(scored):
        source = scored[index][0]
        text = _text_blob(source)
        eligible = request.profile != "agent_skills" or (
            _agent_skills_match(source) and not _contains_any(text, AGENT_OFFTOPIC_TERMS)
        )
        if not eligible:
            triage.decision = "exclude"
            triage.reason += " Excluded because it does not match the profile gate."
        elif triage.total_score >= INCLUDE_SCORE_THRESHOLD and included_count < include_cutoff:
            triage.decision = "include"
            triage.reason += f" Included because score >= {INCLUDE_SCORE_THRESHOLD:.2f} and include quota remains."
            included_count += 1
        elif triage.total_score >= MAYBE_SCORE_THRESHOLD and maybe_count < maybe_cutoff - include_cutoff:
            triage.decision = "maybe"
            triage.reason += f" Marked maybe because score >= {MAYBE_SCORE_THRESHOLD:.2f} but it did not qualify for include."
            maybe_count += 1
        else:
            triage.decision = "exclude"
            triage.reason += " Excluded because its score is below the maybe threshold or the maybe queue is full."
        ranked.append(triage)
    return ranked
