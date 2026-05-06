from __future__ import annotations

from typing import Any

from scholar_forge.bundle import inspect_bundle, read_jsonl, read_yaml
from scholar_forge.cli import main
from scholar_forge.config import load_config
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.pipeline import ScholarPipeline
from scholar_forge.providers.base import ProviderStatus


class FakeProvider:
    name = "fake"

    def status(self, config) -> ProviderStatus:
        return ProviderStatus("fake", True, True, "fixture")

    def fetch(self, query: QueryRecord, request: ResearchRequest, config, *, limit: int) -> Any:
        return {
            "results": [
                {
                    "title": "Protein binder design validation",
                    "abstract": "Protein binder design validation benchmark evidence.",
                    "doi": "10.fake/test",
                }
            ]
        }

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        return [
            SourceRecord(
                source_id="fake1",
                title=item["title"],
                abstract=item["abstract"],
                doi=item["doi"],
                provider="fake",
                year=2024,
                fields=["Biology"],
            )
            for item in raw["results"]
        ]


def test_pipeline_run_with_fake_provider(tmp_path) -> None:
    out = tmp_path / "bundle"
    pipeline = ScholarPipeline(load_config())
    pipeline.providers["fake"] = FakeProvider()
    request = ResearchRequest(question="protein binder design", profile="biomol", providers=["fake"], max_papers=2)
    root = pipeline.run(request, out=out)

    assert root == out
    info = inspect_bundle(out)
    assert info["counts"]["sources"] == 1
    assert info["counts"]["include"] == 1
    assert info["counts"]["evidence"] == 1
    assert info["validation_errors"] == []
    assert (out / "brief.md").read_text(encoding="utf-8").startswith("# Research Brief")


def test_cli_init_plan_inspect(tmp_path) -> None:
    config_path = tmp_path / "scholarforge.yaml"
    out = tmp_path / "bundle"
    assert main(["init", "--path", str(config_path)]) == 0
    assert config_path.exists()
    assert main(["--config", str(config_path), "plan", "agentic research", "--out", str(out)]) == 0
    assert main(["inspect", str(out)]) == 1


def test_cli_plan_uses_config_defaults_when_flags_are_omitted(tmp_path) -> None:
    config_path = tmp_path / "scholarforge.yaml"
    out = tmp_path / "bundle"
    config_path.write_text(
        """
defaults:
  max_papers: 7
  language: zh
  providers:
    - arxiv
providers:
  tavily:
    enabled: false
  semantic_scholar:
    enabled: false
  openalex:
    enabled: false
  pubmed:
    enabled: false
  arxiv:
    enabled: true
""",
        encoding="utf-8",
    )

    assert main(["--config", str(config_path), "plan", "config defaults check", "--out", str(out)]) == 0

    request = read_yaml(out / "request.yaml")
    assert request["max_papers"] == 7
    assert request["language"] == "zh"
    assert request["providers"] == ["arxiv"]


def test_pipeline_llm_triage_updates_decisions(tmp_path, monkeypatch) -> None:
    class FakeLLM:
        def __init__(self, config) -> None:
            self.available = True

        def complete_text(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
            return '{"triage":[{"source_id":"fake1","decision":"exclude","llm_score":0.1,"reason":"Too broad."}]}'

    import scholar_forge.llm

    monkeypatch.setattr(scholar_forge.llm, "OpenAICompatibleLLM", FakeLLM)
    config = load_config()
    config.data["llm"]["api_key"] = "test"
    config.data["llm"]["model"] = "test-model"
    out = tmp_path / "bundle"
    pipeline = ScholarPipeline(config)
    pipeline.providers["fake"] = FakeProvider()
    request = ResearchRequest(
        question="protein binder design",
        profile="biomol",
        providers=["fake"],
        max_papers=2,
        llm_triage=True,
    )

    pipeline.run(request, out=out)

    triage = read_jsonl(out / "triage.jsonl")
    assert triage[0]["decision"] == "exclude"
    assert triage[0]["llm_score"] == 0.1
    assert "Too broad" in triage[0]["llm_reason"]
    provenance = read_jsonl(out / "provenance.jsonl")
    assert any(row["provider"] == "llm_triage" and row["status"] == "ok" for row in provenance)


def test_pipeline_brief_honors_chinese_language(tmp_path) -> None:
    out = tmp_path / "bundle"
    pipeline = ScholarPipeline(load_config())
    pipeline.providers["fake"] = FakeProvider()
    request = ResearchRequest(
        question="protein binder design",
        profile="biomol",
        providers=["fake"],
        max_papers=2,
        language="zh",
        use_llm=False,
    )

    pipeline.run(request, out=out)

    assert (out / "brief.md").read_text(encoding="utf-8").startswith("# 研究简报")
