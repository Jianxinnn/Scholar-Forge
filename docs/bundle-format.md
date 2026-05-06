# Bundle Format

ScholarForge's core product is an auditable evidence bundle. It writes a directory bundle instead of one large JSON file so downstream agents can inspect, diff, reuse, and audit each stage independently.

Current format version: `1.1`

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
    provider/*.json
  notes/
    source_id.md
```

JSONL files support streaming, diffing, partial recovery, and agent-friendly reads. YAML is reserved for configuration and manifests. Markdown is reserved for human review.

## Compatibility Rules

- `bundle_format_version` is required in `manifest.yaml`.
- Minor additions may add optional fields to existing records.
- Existing required fields must keep their names and basic types within a format version.
- Consumers should ignore unknown fields.
- Schema-breaking changes require a new `bundle_format_version`.
- `brief.md` and `notes/*.md` are review aids; JSONL/YAML files are the stable machine contract.

## `manifest.yaml`

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `bundle_id` | string | Stable hash-based bundle identifier. |
| `bundle_format_version` | string | Current value: `1.1`. |
| `created_at` | string | UTC ISO-8601 timestamp for the manifest write. |
| `question` | string | Research question after request defaults are applied. |
| `profile` | string | Active profile after defaults are applied. |
| `counts` | mapping | Counts for `queries`, `sources`, `triage`, and `evidence`. |
| `files` | mapping | Canonical bundle file names. |
| `provenance` | mapping | Manifest-level provenance such as `completed_at`. |

## `request.yaml`

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `question` | string | User research question. |
| `domain` | string | Effective domain after defaults are applied. |
| `profile` | string | Effective profile after defaults are applied. |
| `year_range` | string | Empty string means no year constraint. |
| `max_papers` | integer | Maximum number of included sources. |
| `providers` | list[string] | Enabled provider names used by the request. |
| `constraints` | mapping | Reserved for caller-supplied constraints. |
| `language` | string | Output language hint, for example `en` or `zh`. |
| `read_pdf` | boolean | Whether PDF text extraction was requested. |
| `use_llm` | boolean | Whether LLM-assisted nodes may run. |
| `llm_triage` | boolean | Whether LLM triage was requested. |

## `queries.jsonl`

Each line is a JSON object.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `query` | string | Provider query text. |
| `intent` | string | Query purpose, such as `discovery` or profile-specific intent. |
| `provider_targets` | list[string] | Providers queried for this query. |

Optional fields:

| Field | Type | Notes |
| --- | --- | --- |
| `rationale` | string | Why the query was generated. |

## `sources.jsonl`

Each line is a normalized source record.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `source_id` | string | Stable source identifier. |
| `title` | string | Source title or best available page title. |
| `provider` | string | Provider that produced the normalized record. |

Common optional fields include `source_type`, `abstract`, `snippet`, `authors`, `year`, `venue`, `doi`, `arxiv_id`, `pubmed_id`, `semantic_scholar_id`, `openalex_id`, `url`, `pdf_url`, `citation_count`, `fields`, and `raw`.

## `triage.jsonl`

Each line describes ranking and inclusion status for one source.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `source_id` | string | Matches a `sources.jsonl` source. |
| `decision` | string | One of `include`, `maybe`, or `exclude`. |
| `total_score` | number | Deterministic ranking score from 0 to 1. |

Common optional fields include `relevance_score`, `evidence_score`, `novelty_score`, `reason`, `llm_score`, and `llm_reason`.

## `evidence.jsonl`

Each line captures one evidence item derived from an included source.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `evidence_id` | string | Stable evidence identifier. |
| `source_id` | string | Matches a `sources.jsonl` source. |
| `claim` | string | Conservative claim or context statement. |
| `evidence_text` | string | Evidence excerpt from metadata, abstract, snippet, TLDR, or PDF preview. |

Common optional fields include `evidence_kind`, `supports_or_contradicts`, `confidence`, and `source_locator`.

## `resources.jsonl`

Each line captures one candidate resource entry derived from `sources.jsonl`. Resource extraction is independent of `triage.jsonl`: a source excluded from evidence synthesis may still yield useful resources for downstream tools.

Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `resource_id` | string | Stable resource identifier. |
| `resource_kind` | string | One of `paper`, `web_page`, `full_text`, `pdf`, `structure`, `sequence`, `dataset`, `code`, `protocol`, `patent`, or `other`. |
| `source_ids` | list[string] | Source records that produced or supported this resource. |
| `status` | string | Current first-version value is `candidate`; future values may include `verified` or `failed`. |

Common optional fields include `title`, `url`, `identifiers`, `access`, `providers`, `confidence`, `reason`, and `raw`.

`access` entries may include provider-returned URLs and deterministic derived URLs. Derived URLs must be marked with `source: derived`.

## `provenance.jsonl`

Each line records one pipeline event.

Common fields:

| Field | Type | Notes |
| --- | --- | --- |
| `timestamp` | string | UTC ISO-8601 timestamp. |
| `provider` | string | Provider or pipeline node name. |
| `status` | string | Common values are `ok`, `cached`, `skipped`, and `error`. |
| `query` | string | Query text when the event is provider-search related. |
| `raw_file` | string | Bundle-relative raw artifact path when available. |
| `result_count` | integer | Number of normalized records when available. |
| `error` | string | Error detail for failed events. |
