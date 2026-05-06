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
  -> deterministic ranking
  -> optional LLM triage
  -> evidence extraction
  -> bundle writing
```

The first version treats `scholar-bundle/` as the product. `sources.jsonl`, `triage.jsonl`, `evidence.jsonl`, and `provenance.jsonl` are the primary machine-readable surfaces. `brief.md` is a human audit memo.

## Product Boundaries

ScholarForge does:

- retrieve and normalize scholarly/web sources,
- deduplicate overlapping provider results,
- rank and triage sources,
- optionally apply LLM triage,
- extract conservative evidence records,
- write schema-versioned bundles.

ScholarForge does not do MVP execution, durable claim storage, vector memory, chat orchestration, or final manuscript writing.

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
