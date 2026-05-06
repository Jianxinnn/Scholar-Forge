from __future__ import annotations

from datetime import datetime, timezone

from scholar_forge.bundle import BundleWriter
from scholar_forge.models import ResearchRequest
from scholar_forge.ui.jobs import JobManager, request_from_payload
from scholar_forge.ui.state import create_run_meta, make_run_id, scan_runs, slugify_question, write_run_meta


def test_ui_run_id_slug_is_stable() -> None:
    now = datetime(2026, 5, 6, 15, 30, tzinfo=timezone.utc)
    assert slugify_question("Protein Binder Design!") == "protein-binder-design"
    assert make_run_id("Protein Binder Design!", now=now) == "20260506-153000-protein-binder-design"


def test_ui_run_meta_roundtrip_and_scan(tmp_path) -> None:
    meta = create_run_meta(tmp_path, question="agentic research", profile="agent_skills")
    runs = scan_runs(tmp_path)

    assert (tmp_path / meta.run_id / "run.json").exists()
    assert len(runs) == 1
    assert runs[0].question == "agentic research"
    assert runs[0].status == "queued"


def test_ui_scan_does_not_treat_planning_manifest_as_complete(tmp_path) -> None:
    meta = create_run_meta(tmp_path, question="agentic research", profile="agent_skills")
    meta.status = "running"
    meta.stage = "planned"
    run_dir = tmp_path / meta.run_id
    write_run_meta(run_dir, meta)
    writer = BundleWriter(run_dir)
    writer.write_manifest(ResearchRequest(question="agentic research", profile="agent_skills"), queries=1)

    runs = scan_runs(tmp_path)

    assert runs[0].status == "running"
    assert runs[0].stage == "planned"


def test_ui_request_from_payload_preserves_scope() -> None:
    request = request_from_payload(
        {
            "question": "protein design",
            "profile": "biomol",
            "year_range": "2021-",
            "max_papers": "7",
            "providers": ["pubmed", "openalex"],
            "use_llm": False,
            "llm_triage": True,
        }
    )

    assert request.question == "protein design"
    assert request.profile == "biomol"
    assert request.year_range == "2021-"
    assert request.max_papers == 7
    assert request.providers == ["pubmed", "openalex"]
    assert request.use_llm is False
    assert request.llm_triage is True


def test_ui_job_manager_marks_stale_active_run_interrupted(tmp_path) -> None:
    meta = create_run_meta(tmp_path, question="stale run", profile="general")
    meta.status = "running"
    meta.stage = "searching"
    write_run_meta(tmp_path / meta.run_id, meta)
    manager = JobManager(tmp_path)

    runs = manager.list_runs()

    assert runs[0].status == "error"
    assert runs[0].stage == "interrupted"
    assert "interrupted" in runs[0].error
