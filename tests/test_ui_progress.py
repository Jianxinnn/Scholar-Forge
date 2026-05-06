from __future__ import annotations

from scholar_forge.bundle import BundleWriter
from scholar_forge.models import ResearchRequest
from scholar_forge.ui.progress import build_progress_summary
from scholar_forge.ui.state import RunMeta


def test_ui_progress_summary_builds_steps_and_provider_events(tmp_path) -> None:
    writer = BundleWriter(tmp_path)
    request = ResearchRequest(question="protein design", providers=["openalex"], use_llm=False)
    writer.write_request(request)
    writer.write_queries([])
    writer.append_provenance(
        {
            "timestamp": "2026-05-06T12:00:00+00:00",
            "provider": "openalex",
            "query": "protein design",
            "status": "ok",
            "result_count": 10,
        }
    )
    meta = RunMeta(
        run_id="run1",
        status="running",
        stage="searching",
        created_at="2026-05-06T12:00:00+00:00",
        bundle_path=str(tmp_path),
        counts={"queries": 1},
    )

    summary = build_progress_summary(tmp_path, meta)

    assert summary["steps"][1]["key"] == "searching"
    assert summary["steps"][1]["state"] == "active"
    assert summary["providers"][0]["provider"] == "openalex"
    assert summary["providers"][0]["results"] == 10
    assert summary["events"][0]["detail"] == "10 results"
