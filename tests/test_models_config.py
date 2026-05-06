from __future__ import annotations

from scholar_forge.config import load_config
from scholar_forge.models import ResearchRequest, SourceRecord
from scholar_forge.pipeline import ScholarPipeline
from scholar_forge.utils import title_fingerprint


def test_research_request_from_dict_preserves_unspecified_defaults() -> None:
    request = ResearchRequest.from_dict({"question": "What works?", "domain": "biomol"})
    assert request.question == "What works?"
    assert request.domain == "biomol"
    assert request.profile == "biomol"
    assert request.max_papers is None
    assert request.use_llm is True


def test_pipeline_apply_defaults_uses_config_defaults(tmp_path) -> None:
    cfg_path = tmp_path / "scholarforge.yaml"
    cfg_path.write_text(
        """
defaults:
  max_papers: 7
  domain: biomol
  language: zh
  providers:
    - arxiv
""",
        encoding="utf-8",
    )
    request = ResearchRequest(question="What works?")
    resolved = ScholarPipeline.from_config(cfg_path).apply_defaults(request)
    assert resolved.domain == "biomol"
    assert resolved.profile == "biomol"
    assert resolved.max_papers == 7
    assert resolved.language == "zh"
    assert resolved.providers == ["arxiv"]


def test_source_record_from_dict() -> None:
    source = SourceRecord.from_dict({"source_id": "s1", "title": "Paper", "authors": ["A"], "year": 2024})
    assert source.source_id == "s1"
    assert source.authors == ["A"]
    assert source.year == 2024


def test_config_env_expansion(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SCHOLARFORGE_LLM_API_KEY", "abc")
    cfg_path = tmp_path / "scholarforge.yaml"
    cfg_path.write_text(
        """
llm:
  api_key: ${SCHOLARFORGE_LLM_API_KEY}
  model: test-model
providers:
  tavily:
    enabled: false
""",
        encoding="utf-8",
    )
    config = load_config(cfg_path)
    assert config.llm_api_key == "abc"
    assert config.llm_model == "test-model"
    assert config.provider_enabled("tavily") is False


def test_title_fingerprint_is_stable() -> None:
    assert title_fingerprint("The Protein Design Method v2!") == "protein design method"
