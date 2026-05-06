# ScholarForge Architecture

ScholarForge is a bundle-first scholarly evidence compiler for agents.

The architectural goal is narrow: turn a research question into an auditable `scholar-bundle/` that downstream agents can inspect and reuse. Human-readable text is generated from the bundle; it is not the source of truth.

```text
Research question in -> auditable evidence bundle out
```

The runtime is a deterministic research pipeline with optional LLM-assisted nodes.

```text
ResearchRequest
  -> query planning
  -> provider search
  -> source normalization
  -> deduplication
  -> resource extraction
  -> deterministic ranking
  -> optional LLM triage
  -> evidence extraction
  -> bundle writing
```

The first version treats `scholar-bundle/` as the product. `sources.jsonl`, `resources.jsonl`, `triage.jsonl`, `evidence.jsonl`, and `provenance.jsonl` are the primary machine-readable surfaces. `brief.md` is a human audit memo.

## Product Boundaries

ScholarForge does:

- retrieve and normalize scholarly/web sources,
- deduplicate overlapping provider results,
- extract candidate resources independently from evidence triage,
- rank and triage sources,
- optionally apply LLM triage,
- extract conservative evidence records,
- write schema-versioned bundles.

ScholarForge does not do MVP execution, durable claim storage, vector memory, chat orchestration, or final manuscript writing.

## Optional Local UI

The local Web UI is an optional interface, not a new persistence layer. It is installed with the `ui` extra and started with:

```bash
scholar-forge ui
```

UI boundaries:

- local single-user server only, bound to `127.0.0.1` by default,
- no database,
- no account system,
- no API key management,
- no durable chat memory,
- no changes to the bundle format.

The UI writes runs under `./scholar-runs/<timestamp>-<slug>/` by default. Each run directory is a normal ScholarForge bundle plus a UI-only `run.json` file for job status such as `queued`, `running`, `done`, `error`, or `cancelled`. `run.json` is not part of the bundle contract and should be ignored by downstream bundle consumers.

The result page reads bundle artifacts directly and presents a read-only audit view for `brief.md`, sources, triage, evidence, resources, and provenance. Follow-up questions are scoped to the current bundle. Deterministic quick actions inspect bundle records directly; optional LLM synthesis uses a compressed bundle context and must cite source or evidence identifiers.

The core pipeline exposes only generic `progress` and `should_cancel` hooks for UI observability and best-effort cancellation. These hooks do not depend on FastAPI or UI concepts, and CLI/Python API behavior remains unchanged when hooks are omitted.

## Provider Order

Default providers:

1. Tavily
2. Semantic Scholar
3. OpenAlex
4. PubMed
5. arXiv

Google Scholar/Serper can be added later as an optional provider.

## LLM Policy

The LLM adapter is OpenAI-compatible only. It reads:

```text
SCHOLARFORGE_LLM_BASE_URL
SCHOLARFORGE_LLM_API_KEY
SCHOLARFORGE_LLM_MODEL
```

The default model is `gpt-5.2`. The pipeline must still work in `--no-llm` mode.
