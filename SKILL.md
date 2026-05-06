---
name: scholar-forge-repo
description: Use this repository as a bundle-first scholarly evidence compiler for agents. Read when an agent is working inside the ScholarForge repo and needs to turn a research question into an auditable scholar-bundle, inspect bundle evidence, or modify the ScholarForge codebase.
---

# ScholarForge Agent Entry

This root `SKILL.md` is the canonical onboarding file for agents that read the repository directory directly.

Core positioning:

```text
Research question in -> auditable evidence bundle out
```

ScholarForge can be used in two modes:

- Standalone tool: run the `scholar-forge` CLI or import the `scholar_forge` Python API.
- Agent tool: compile a `scholar-bundle/` that another agent can inspect, audit, and reuse.

Do not treat ScholarForge as a chat app, vector-memory system, final survey writer, or execution engine. The bundle is the product; `brief.md` is only an audit memo.

The package internals live in `src/scholar_forge/`. Agents reading this repo should start here and treat this root file as the only agent onboarding entry.

## Fast Path

Default to the installed CLI. If the package is not installed and you are working from this repository, replace `scholar-forge` with `uv run scholar-forge`.

```bash
scholar-forge doctor
scholar-forge plan "$QUESTION" --out ./scholar-bundle
scholar-forge run "$QUESTION" --out ./scholar-bundle
scholar-forge inspect ./scholar-bundle
```

For biomolecular research:

```bash
scholar-forge run "$QUESTION" --profile biomol --out ./scholar-bundle
```

For LLM-assisted triage:

```bash
scholar-forge run "$QUESTION" --llm-triage --out ./scholar-bundle
```

For full-text checks on selected included PDFs:

```bash
scholar-forge run "$QUESTION" --read-pdf --out ./scholar-bundle
```

## What To Read After A Run

Read bundle files in this order:

```text
scholar-bundle/brief.md
scholar-bundle/triage.jsonl
scholar-bundle/evidence.jsonl
scholar-bundle/resources.jsonl
scholar-bundle/sources.jsonl
scholar-bundle/provenance.jsonl
```

Treat `brief.md` as an audit memo, not a final survey. Use `evidence.jsonl`, `resources.jsonl`, `triage.jsonl`, `sources.jsonl`, and `provenance.jsonl` for decisions that need traceability.

## Profiles

- `general`: broad scholarly search.
- `biomol`: protein design, binder design, enzyme engineering, structure prediction, wet-lab validation, benchmarks, reproducibility, and safety caveats.
- `agent_skills`: LLM agent skill libraries, self-improving agents, tool use, skill acquisition, memory, reflection, and governance.

## Configuration

Configuration precedence:

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

## Bundle Contract

ScholarForge writes directory bundles. The machine contract is documented in `docs/bundle-format.md`.

Expected files:

```text
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

`manifest.yaml` includes `bundle_format_version: '1.1'`. `scholar-forge inspect` validates required files and basic schema.

## Examples

- Integration examples live in `examples/integrations/`.
- Example bundles live in `examples/bundles/`.

## Development

Run tests with:

```bash
pytest
```

If development dependencies are not installed and `uv` is available, use `uv run pytest`.

Important source paths:

- CLI: `src/scholar_forge/cli.py`
- Pipeline: `src/scholar_forge/pipeline.py`
- Bundle IO and validation: `src/scholar_forge/bundle.py`
- Models: `src/scholar_forge/models.py`
- Provider integrations: `src/scholar_forge/providers/`
- LLM adapter: `src/scholar_forge/llm/openai_compatible.py`
- PDF reader: `src/scholar_forge/readers/pdf.py`

Keep the core lightweight and framework-free. Do not add LangChain, Agno, LiteLLM, vector databases, or daemon state for MVP work. Default tests must stay offline and deterministic.
