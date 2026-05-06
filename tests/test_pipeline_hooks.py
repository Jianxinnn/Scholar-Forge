from __future__ import annotations

from typing import Any

import pytest

from scholar_forge.config import load_config
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.pipeline import PipelineCancelled, ScholarPipeline
from scholar_forge.providers.base import ProviderStatus


class HookProvider:
    name = "hook"

    def status(self, config) -> ProviderStatus:
        return ProviderStatus("hook", True, True, "fixture")

    def fetch(self, query: QueryRecord, request: ResearchRequest, config, *, limit: int) -> Any:
        return {"results": [{"title": "agentic research evidence"}]}

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        return [
            SourceRecord(
                source_id="hook1",
                title="agentic research evidence",
                abstract="Agentic research evidence for deterministic testing.",
                provider="hook",
                year=2024,
            )
        ]


def test_pipeline_progress_hook_preserves_default_behavior(tmp_path) -> None:
    out = tmp_path / "bundle"
    stages: list[str] = []
    pipeline = ScholarPipeline(load_config())
    pipeline.providers["hook"] = HookProvider()
    request = ResearchRequest(
        question="agentic research evidence",
        providers=["hook"],
        max_papers=1,
        use_llm=False,
    )

    root = pipeline.run(request, out=out, progress=lambda stage, detail: stages.append(stage))

    assert root == out
    assert "planning" in stages
    assert "searching" in stages
    assert "done" in stages
    assert (out / "sources.jsonl").exists()


def test_pipeline_cancel_hook_stops_at_stage_boundary(tmp_path) -> None:
    out = tmp_path / "bundle"
    cancel = {"value": False}
    pipeline = ScholarPipeline(load_config())
    pipeline.providers["hook"] = HookProvider()
    request = ResearchRequest(
        question="agentic research evidence",
        providers=["hook"],
        max_papers=1,
        use_llm=False,
    )

    def progress(stage: str, detail: dict[str, Any]) -> None:
        if stage == "planned":
            cancel["value"] = True

    with pytest.raises(PipelineCancelled):
        pipeline.run(request, out=out, progress=progress, should_cancel=lambda: cancel["value"])

    assert (out / "request.yaml").exists()
    assert (out / "queries.jsonl").exists()
    assert not (out / "sources.jsonl").exists()
