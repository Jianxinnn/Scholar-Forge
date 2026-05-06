from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_PROVIDER_ORDER = ["tavily", "semantic_scholar", "openalex", "pubmed", "arxiv"]


DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {
        "base_url": "",
        "api_key": "",
        "model": "gpt-5.2",
    },
    "providers": {
        "tavily": {"enabled": True, "api_key": "", "base_url": ""},
        "semantic_scholar": {"enabled": True, "api_key": ""},
        "openalex": {"enabled": True, "email": ""},
        "pubmed": {"enabled": True, "email": "", "api_key": ""},
        "arxiv": {"enabled": True},
    },
    "defaults": {
        "max_papers": 30,
        "max_search_results_per_query": 10,
        "year": "",
        "domain": "general",
        "language": "en",
        "providers": DEFAULT_PROVIDER_ORDER,
    },
    "profiles": {
        "general": {
            "query_expansions": ["review", "survey", "recent advances"],
            "evidence_focus": ["method", "result", "limitation", "comparison"],
        },
        "biomol": {
            "providers": ["semantic_scholar", "pubmed", "openalex", "tavily", "arxiv"],
            "query_expansions": [
                "protein design",
                "binder design",
                "enzyme engineering",
                "structure prediction",
                "wet-lab validation",
            ],
            "evidence_focus": [
                "dataset",
                "benchmark",
                "method",
                "validation",
                "limitation",
                "reproducibility",
                "safety",
            ],
        },
        "agent_skills": {
            "providers": ["tavily", "semantic_scholar", "openalex", "arxiv"],
            "query_expansions": [
                "LLM agent skill library",
                "self-improving agents",
                "self-evolving agents",
                "tool use",
                "lifelong learning",
                "memory reflection",
                "SKILL.md",
                "Model Context Protocol",
            ],
            "evidence_focus": [
                "skill acquisition",
                "skill library",
                "self-improvement loop",
                "experience replay",
                "tool-grounded learning",
                "evaluation",
                "security",
            ],
        },
    },
}


CONFIG_TEMPLATE = """# ScholarForge configuration
llm:
  base_url: ${SCHOLARFORGE_LLM_BASE_URL}
  api_key: ${SCHOLARFORGE_LLM_API_KEY}
  model: gpt-5.2

providers:
  tavily:
    enabled: true
    api_key: ${TAVILY_API_KEY}
    base_url: ${TAVILY_BASE_URL}
  semantic_scholar:
    enabled: true
    api_key: ${S2_API_KEY}
  openalex:
    enabled: true
    email: ${OPENALEX_EMAIL}
  pubmed:
    enabled: true
    email: ${NCBI_EMAIL}
    api_key: ${NCBI_API_KEY}
  arxiv:
    enabled: true

defaults:
  max_papers: 30
  max_search_results_per_query: 10
  year: ""
  domain: general
  language: en
  providers:
    - tavily
    - semantic_scholar
    - openalex
    - pubmed
    - arxiv
"""


ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return ENV_PATTERN.sub(lambda m: os.getenv(m.group(1), ""), value)
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def env_config() -> dict[str, Any]:
    return {
        "llm": {
            "base_url": os.getenv("SCHOLARFORGE_LLM_BASE_URL", ""),
            "api_key": os.getenv("SCHOLARFORGE_LLM_API_KEY", ""),
            "model": os.getenv("SCHOLARFORGE_LLM_MODEL", "gpt-5.2"),
        },
        "providers": {
            "tavily": {
                "api_key": os.getenv("TAVILY_API_KEY", ""),
                "base_url": os.getenv("TAVILY_BASE_URL", ""),
            },
            "semantic_scholar": {
                "api_key": os.getenv("S2_API_KEY", os.getenv("Semantic_Search_API_KEY", ""))
            },
            "openalex": {"email": os.getenv("OPENALEX_EMAIL", "")},
            "pubmed": {
                "email": os.getenv("NCBI_EMAIL", ""),
                "api_key": os.getenv("NCBI_API_KEY", ""),
            },
        },
    }


@dataclass(slots=True)
class ScholarForgeConfig:
    data: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_CONFIG))
    path: Path | None = None

    @property
    def llm_base_url(self) -> str:
        return str(self.data.get("llm", {}).get("base_url", "") or "")

    @property
    def llm_api_key(self) -> str:
        return str(self.data.get("llm", {}).get("api_key", "") or "")

    @property
    def llm_model(self) -> str:
        return str(self.data.get("llm", {}).get("model", "gpt-5.2") or "gpt-5.2")

    def provider_config(self, name: str) -> dict[str, Any]:
        return dict(self.data.get("providers", {}).get(name, {}) or {})

    def provider_enabled(self, name: str) -> bool:
        return bool(self.provider_config(name).get("enabled", True))

    def provider_api_key(self, name: str) -> str:
        cfg = self.provider_config(name)
        if name == "semantic_scholar":
            return str(cfg.get("api_key", "") or os.getenv("S2_API_KEY", ""))
        return str(cfg.get("api_key", "") or "")

    def provider_email(self, name: str) -> str:
        return str(self.provider_config(name).get("email", "") or "")

    def default_providers(self, profile: str = "general") -> list[str]:
        profile_cfg = self.profile(profile)
        default_providers = list(self.data.get("defaults", {}).get("providers") or DEFAULT_PROVIDER_ORDER)
        profile_providers = profile_cfg.get("providers")
        builtin_profile_providers = (DEFAULT_CONFIG.get("profiles", {}).get(profile, {}) or {}).get("providers")
        if profile_providers and list(profile_providers) != list(builtin_profile_providers or []):
            return list(profile_providers)
        if default_providers != DEFAULT_PROVIDER_ORDER:
            return default_providers
        return list(profile_providers or default_providers)

    def default_max_papers(self) -> int:
        return int(self.data.get("defaults", {}).get("max_papers", 30) or 30)

    def default_year(self) -> str:
        return str(self.data.get("defaults", {}).get("year", "") or "")

    def default_domain(self) -> str:
        return str(self.data.get("defaults", {}).get("domain", "general") or "general")

    def default_language(self) -> str:
        return str(self.data.get("defaults", {}).get("language", "en") or "en")

    def max_search_results_per_query(self) -> int:
        return int(self.data.get("defaults", {}).get("max_search_results_per_query", 10) or 10)

    def profile(self, name: str) -> dict[str, Any]:
        profiles = self.data.get("profiles", {})
        return dict(profiles.get(name) or profiles.get("general") or {})


def load_config(config_path: str | Path | None = None) -> ScholarForgeConfig:
    data = deep_merge(DEFAULT_CONFIG, env_config())
    path: Path | None = None

    candidate = Path(config_path) if config_path else Path.cwd() / "scholarforge.yaml"
    if candidate.exists():
        path = candidate
        loaded = yaml.safe_load(_expand_env(candidate.read_text(encoding="utf-8"))) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config file must contain a YAML mapping: {candidate}")
        data = deep_merge(data, loaded)

    return ScholarForgeConfig(data=data, path=path)


def write_config_template(path: str | Path, *, force: bool = False) -> Path:
    p = Path(path)
    if p.exists() and not force:
        raise FileExistsError(f"Config already exists: {p}")
    p.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    return p
