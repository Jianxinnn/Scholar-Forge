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
- Optional local Web UI: `scholar-forge ui`
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

## Local Web UI

ScholarForge includes an optional local, single-user Web UI for search-style bundle creation and review.

```bash
python3 -m pip install -e ".[ui]"
scholar-forge ui
```

If you are using `uv` from the repository:

```bash
uv run --extra ui scholar-forge ui
```

Defaults:

- URL: `http://127.0.0.1:8765`
- Runs directory: `./scholar-runs`
- Override runs directory: `scholar-forge ui --runs-dir ./my-runs`

The UI is a thin local interface over the existing bundle pipeline:

- each search creates a new `scholar-runs/<timestamp>-<slug>/` bundle,
- persisted research data remains the standard bundle files,
- `run.json` is UI-only job metadata and is not part of the bundle contract,
- the result page is a read-only audit view,
- follow-up answers are grounded in the current bundle and are not persisted,
- provider and LLM keys still come from `scholarforge.yaml` or environment variables.

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
  resources.jsonl
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
- Downstream agents should rely on `sources.jsonl`, `resources.jsonl`, `triage.jsonl`, `evidence.jsonl`, and `provenance.jsonl` for traceable decisions.
- Cairn should record durable claims, artifacts, hypotheses, and links after evidence is reviewed.
- BioMolHarness should consume bundles as task context or constraints, not as execution proof.
- AutoSkills should use bundles only as background evidence; skill promotion still requires execution evidence.
- ScholarForge should not grow into a daemon, vector database, durable chat system, or long-form manuscript generator for the MVP.
