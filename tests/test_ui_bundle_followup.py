from __future__ import annotations

from scholar_forge.bundle import BundleWriter
from scholar_forge.models import EvidenceRecord, ResearchRequest, ResourceRecord, SourceRecord, TriageRecord
from scholar_forge.ui.bundle_view import load_bundle_view
from scholar_forge.ui.followup import answer_followup, build_llm_context


def _write_fixture_bundle(out) -> None:
    writer = BundleWriter(out)
    request = ResearchRequest(
        question="agentic research evidence",
        profile="agent_skills",
        max_papers=1,
        providers=["fake"],
        use_llm=False,
    )
    source = SourceRecord(
        source_id="src_test",
        title="Agentic Research Evidence",
        abstract="Large language model agents can use tools and reflection.",
        provider="fake",
        year=2024,
        url="https://example.com/paper",
    )
    triage = TriageRecord(
        source_id="src_test",
        relevance_score=0.8,
        evidence_score=0.7,
        novelty_score=1.0,
        total_score=0.82,
        decision="include",
        reason="Included by fixture.",
    )
    evidence = EvidenceRecord(
        evidence_id="ev_test",
        source_id="src_test",
        claim="Agentic research evidence provides context.",
        evidence_text="Large language model agents can use tools and reflection.",
        confidence=0.6,
    )
    resource = ResourceRecord(
        resource_id="res_code",
        resource_kind="code",
        source_ids=["src_test"],
        title="Example code",
        url="https://github.com/example/repo",
    )
    writer.write_request(request)
    writer.write_queries([])
    writer.write_sources([source])
    writer.write_triage([triage])
    writer.write_evidence([evidence])
    writer.write_resources([resource])
    writer.write_brief("# Brief\n\n<script>alert(1)</script>\n\nUseful evidence.")
    writer.write_references("")
    writer.write_manifest(request, sources=1, triage=1, evidence=1, resources=1)


def test_ui_bundle_view_joins_records_and_sanitizes_brief(tmp_path) -> None:
    _write_fixture_bundle(tmp_path)

    view = load_bundle_view(tmp_path)

    assert view["sources"][0]["source_id"] == "src_test"
    assert view["sources"][0]["triage"]["decision"] == "include"
    assert view["sources"][0]["evidence_count"] == 1
    assert "<script" not in view["brief_html"]
    assert view["artifacts"]["brief"] is True


def test_ui_followup_deterministic_intents(tmp_path) -> None:
    _write_fixture_bundle(tmp_path)
    view = load_bundle_view(tmp_path)

    top = answer_followup(view, intent="top_sources")
    why = answer_followup(view, intent="why_decision", source_id="src_test")
    evidence = answer_followup(view, intent="evidence_for", source_id="src_test")
    resources = answer_followup(view, intent="resources_by_kind")

    assert "[src_test]" in top["answer"]
    assert "`include`" in why["answer"]
    assert "[ev_test]" in evidence["answer"]
    assert "code: 1" in resources["answer"]


def test_ui_llm_context_is_bounded_to_bundle_records(tmp_path) -> None:
    _write_fixture_bundle(tmp_path)
    view = load_bundle_view(tmp_path)

    context = build_llm_context(view)

    assert "src_test" in context
    assert "ev_test" in context
    assert "Example code" in context
