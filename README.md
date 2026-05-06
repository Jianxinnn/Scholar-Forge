# ScholarForge

ScholarForge is a bundle-first scholarly evidence compiler for agents.

It turns a research question into an auditable `scholar-bundle/` containing planned queries, normalized sources, triage decisions, extracted evidence, provenance, notes, and references. The bundle is designed for downstream agents and tools to inspect, reuse, and audit.

ScholarForge is not a chat app, not a vector-memory system, and not a final survey writer. The MVP focuses on retrieval, normalization, deduplication, ranking, optional LLM triage, evidence extraction, and bundle generation.

```text
Research question in -> auditable evidence bundle out
```

## Interfaces

- CLI: `scholar-forge`
- Python API: `scholar_forge`
- Agent entry: root `SKILL.md`
- Bundle contract: `docs/bundle-format.md`

MCP is intentionally not part of the first version.

When this repository is given directly to Codex, Claude Code, or another coding agent, the canonical onboarding file is `./SKILL.md`.

## Quick Start

```bash
python3 -m pip install -e ".[dev,pdf]"
scholar-forge init
scholar-forge doctor
scholar-forge plan "protein binder design with diffusion models" --profile biomol --out ./scholar-bundle
scholar-forge run "protein binder design with diffusion models" --profile biomol --out ./scholar-bundle
scholar-forge inspect ./scholar-bundle
```

If you are working directly from this repository and prefer `uv`, replace `scholar-forge` with `uv run scholar-forge`.

## Configuration

Configuration priority:

```text
CLI flags
> request.yaml
> scholarforge.yaml
> environment variables
> built-in defaults
```

Common environment variables:

```bash
SCHOLARFORGE_LLM_BASE_URL=
SCHOLARFORGE_LLM_API_KEY=
SCHOLARFORGE_LLM_MODEL=gpt-5.2

TAVILY_API_KEY=
S2_API_KEY=
OPENALEX_EMAIL=
NCBI_EMAIL=
NCBI_API_KEY=
```

## Bundle Format

```text
scholar-bundle/
  manifest.yaml
  request.yaml
  queries.jsonl
  sources.jsonl
  triage.jsonl
  evidence.jsonl
  brief.md
  references.bib
  provenance.jsonl
  raw/
  notes/
```

## Python API

```python
from scholar_forge import run_research
from scholar_forge.models import ResearchRequest

request = ResearchRequest(
    question="protein binder design with diffusion models",
    domain="biomol",
    profile="biomol",
    year_range="2021-",
    max_papers=30,
)

bundle = run_research(request, out="./scholar-bundle")
print(bundle)
```

## Examples

- Integration examples: `examples/integrations/`
- Example bundles: `examples/bundles/`

## Design Boundaries

- ScholarForge produces auditable research evidence bundles.
- The bundle is the product; `brief.md` is a human audit memo, not the primary data store.
- Downstream agents should rely on `sources.jsonl`, `triage.jsonl`, `evidence.jsonl`, and `provenance.jsonl` for traceable decisions.
- Cairn should record durable claims, artifacts, hypotheses, and links after evidence is reviewed.
- BioMolHarness should consume bundles as task context or constraints, not as execution proof.
- AutoSkills should use bundles only as background evidence; skill promotion still requires execution evidence.
- ScholarForge should not grow into a daemon, vector database, chat interface, or long-form manuscript generator for the MVP.
