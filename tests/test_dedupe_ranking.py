from __future__ import annotations

from scholar_forge.dedupe import dedupe_sources
from scholar_forge.models import ResearchRequest, SourceRecord
from scholar_forge.ranking import rank_sources


def test_dedupe_merges_by_doi_and_title() -> None:
    s1 = SourceRecord(
        source_id="s1",
        title="Protein Binder Design with Diffusion Models",
        doi="10.123/example",
        provider="semantic_scholar",
        abstract="A method for protein binder design.",
    )
    s2 = SourceRecord(
        source_id="s2",
        title="The protein binder design with diffusion models",
        doi="10.123/example",
        provider="openalex",
        pdf_url="https://example.test/paper.pdf",
    )
    deduped = dedupe_sources([s1, s2])
    assert len(deduped) == 1
    assert deduped[0].pdf_url
    assert sorted(deduped[0].raw["providers_seen"]) == ["openalex", "semantic_scholar"]


def test_ranking_includes_top_n() -> None:
    request = ResearchRequest(question="protein binder design", profile="biomol", max_papers=1)
    strong = SourceRecord(
        source_id="strong",
        title="Protein binder design benchmark",
        abstract="Protein binder design methods and validation benchmark.",
        provider="pubmed",
        year=2024,
        citation_count=50,
        fields=["Biology"],
    )
    weak = SourceRecord(source_id="weak", title="Unrelated", abstract="Other topic.", provider="arxiv", year=2010)
    triage = rank_sources(request, [weak, strong])
    assert triage[0].source_id == "strong"
    assert triage[0].decision == "include"
    assert triage[1].decision == "exclude"


def test_ranking_does_not_include_low_score_sources_to_fill_quota() -> None:
    request = ResearchRequest(question="protein binder design", profile="biomol", max_papers=3)
    weak = SourceRecord(
        source_id="weak",
        title="Unrelated classroom survey",
        abstract="This paper studies unrelated behavior.",
        provider="openalex",
        year=2025,
    )

    triage = rank_sources(request, [weak])

    assert triage[0].decision == "exclude"


def test_agent_skills_profile_excludes_education_skill_noise() -> None:
    request = ResearchRequest(question="self-evolving agent skills", profile="agent_skills", max_papers=3)
    relevant = SourceRecord(
        source_id="agent",
        title="LLM Agent Skill Library with Self-Improvement",
        abstract="Large language model agents acquire reusable skills through tool use and reflection.",
        provider="semantic_scholar",
        year=2026,
        fields=["Computer Science"],
    )
    noise = SourceRecord(
        source_id="education",
        title="Student perception of self-directed learning skills",
        abstract="This education study measures student skill development.",
        provider="openalex",
        year=2025,
    )
    triage = rank_sources(request, [noise, relevant])
    by_id = {row.source_id: row for row in triage}
    assert by_id["agent"].decision == "include"
    assert by_id["education"].decision == "exclude"
