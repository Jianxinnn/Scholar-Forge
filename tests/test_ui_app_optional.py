from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient

from scholar_forge.ui.app import create_app


def test_ui_app_renders_index_when_optional_dependencies_are_installed(tmp_path) -> None:
    client = TestClient(create_app(runs_dir=tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Search research evidence" in response.text


def test_ui_app_progress_endpoint_for_existing_run(tmp_path) -> None:
    from scholar_forge.bundle import BundleWriter
    from scholar_forge.models import ResearchRequest
    from scholar_forge.ui.state import create_run_meta

    meta = create_run_meta(tmp_path, question="protein design", profile="general")
    writer = BundleWriter(tmp_path / meta.run_id)
    writer.write_request(ResearchRequest(question="protein design", providers=["openalex"], use_llm=False))
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
    client = TestClient(create_app(runs_dir=tmp_path))

    response = client.get(f"/api/runs/{meta.run_id}/progress")

    assert response.status_code == 200
    assert response.json()["providers"][0]["provider"] == "openalex"
