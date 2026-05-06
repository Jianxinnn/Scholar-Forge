from __future__ import annotations

from scholar_forge.bundle import BUNDLE_FORMAT_VERSION, inspect_bundle, read_jsonl, read_yaml
from scholar_forge.config import load_config
from scholar_forge.models import QueryRecord, ResearchRequest
from scholar_forge.pipeline import ScholarPipeline


def test_biomol_plan_writes_bundle(tmp_path) -> None:
    out = tmp_path / "bundle"
    pipeline = ScholarPipeline(load_config())
    request = ResearchRequest(question="diffusion models for binder design", profile="biomol", max_papers=5)
    queries = pipeline.plan(request, out=out)

    assert len(queries) >= 3
    assert any(q.intent == "biomol_validation" for q in queries)
    assert (out / "request.yaml").exists()
    assert (out / "queries.jsonl").exists()

    loaded = read_jsonl(out / "queries.jsonl", QueryRecord)
    assert len(loaded) == len(queries)

    info = inspect_bundle(out)
    assert info["counts"]["queries"] == len(queries)
    assert info["files"]["manifest"] is True
    assert info["files"]["resources"] is False
    manifest = read_yaml(out / "manifest.yaml")
    assert manifest["bundle_format_version"] == BUNDLE_FORMAT_VERSION
    assert manifest["files"]["resources"] == "resources.jsonl"
