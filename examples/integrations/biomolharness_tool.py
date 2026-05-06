"""Example BioMolHarness-style wrapper for ScholarForge.

This is an integration sketch. ScholarForge stays independent; BioMolHarness
can call the Python API or CLI from an optional tool.
"""

from __future__ import annotations

from pathlib import Path

from scholar_forge import run_research
from scholar_forge.models import ResearchRequest


def research_literature(question: str, out: str = "./scholar-bundle") -> dict[str, str]:
    request = ResearchRequest(
        question=question,
        profile="biomol",
        domain="biomol",
        year_range="2020-",
        max_papers=30,
    )
    bundle = run_research(request, out=out)
    return {
        "bundle": str(bundle),
        "brief": str(Path(bundle) / "brief.md"),
        "evidence": str(Path(bundle) / "evidence.jsonl"),
    }

