# ScholarForge Architecture Diagram

This diagram captures the current MVP architecture and execution route.

ScholarForge's product shape is:

```text
Research question in -> auditable evidence bundle out
```

## System Boundaries

```mermaid
flowchart LR
    User["User / Agent"] --> CLI["CLI<br/>scholar-forge"]
    User --> API["Python API<br/>scholar_forge"]
    RootSkill["Repo Agent Entry<br/>SKILL.md"] --> CLI

    CLI --> Pipeline["ScholarPipeline"]
    API --> Pipeline

    Pipeline --> Config["Config Layer<br/>CLI flags > request.yaml > scholarforge.yaml > env > defaults"]
    Pipeline --> Planner["Query Planner"]
    Pipeline --> Providers["Provider Registry"]
    Pipeline --> Dedupe["Deduplication"]
    Pipeline --> Ranking["Deterministic Ranking<br/>threshold + max_papers cap"]
    Pipeline --> LLMTriage["Optional LLM Triage"]
    Pipeline --> PDF["Optional PDF Reader"]
    Pipeline --> Evidence["Evidence Extraction"]
    Pipeline --> Brief["Brief Writer<br/>en / zh"]
    Pipeline --> Bundle["Bundle Writer"]

    Providers --> Tavily["Tavily"]
    Providers --> SemanticScholar["Semantic Scholar"]
    Providers --> OpenAlex["OpenAlex"]
    Providers --> PubMed["PubMed"]
    Providers --> Arxiv["arXiv"]

    LLMTriage --> LLM["OpenAI-compatible LLM"]
    Brief --> LLM

    Bundle --> Output["scholar-bundle/<br/>auditable evidence contract"]
```

## Pipeline Route

```mermaid
flowchart TD
    Start["ResearchRequest<br/>question, profile, domain, limits"] --> Defaults["Apply Defaults<br/>config + request merge"]
    Defaults --> Plan["Plan Queries<br/>queries.jsonl"]
    Plan --> Search["Search Providers<br/>raw/provider/*.json"]
    Search --> Normalize["Normalize Sources<br/>SourceRecord"]
    Normalize --> Dedupe["Deduplicate<br/>DOI / provider IDs / title fingerprint"]
    Dedupe --> Rank["Rank Sources<br/>keyword + evidence + recency + impact + profile"]
    Rank --> Threshold["Assign Decisions<br/>include / maybe / exclude"]
    Threshold --> MaybeLLM{"llm_triage?"}

    MaybeLLM -- "yes" --> LLMTriage["LLM Triage Override<br/>bounded by max_papers"]
    MaybeLLM -- "no" --> MaybePDF{"read_pdf?"}
    LLMTriage --> MaybePDF

    MaybePDF -- "yes" --> ReadPDF["Download + Extract Top PDFs<br/>pdf_text_preview"]
    MaybePDF -- "no" --> Evidence
    ReadPDF --> Evidence["Extract Evidence<br/>included sources only"]

    Evidence --> Sources["Write sources.jsonl"]
    Sources --> Triage["Write triage.jsonl"]
    Triage --> EvidenceFile["Write evidence.jsonl"]
    EvidenceFile --> Notes["Write notes/*.md"]
    Notes --> Brief["Write brief.md"]
    Brief --> Bib["Write references.bib"]
    Bib --> Manifest["Write manifest.yaml<br/>bundle_format_version: 1.0"]
    Manifest --> Done["Inspectable Bundle<br/>Files: ok / Schema: ok"]
```

## Bundle Contract

```mermaid
flowchart LR
    Bundle["scholar-bundle/"] --> Manifest["manifest.yaml<br/>version, counts, file map"]
    Bundle --> Request["request.yaml<br/>effective request"]
    Bundle --> Queries["queries.jsonl<br/>planned provider queries"]
    Bundle --> Sources["sources.jsonl<br/>normalized sources"]
    Bundle --> Triage["triage.jsonl<br/>scores and decisions"]
    Bundle --> Evidence["evidence.jsonl<br/>claim-linked excerpts"]
    Bundle --> Brief["brief.md<br/>human audit memo"]
    Bundle --> Bib["references.bib<br/>included references"]
    Bundle --> Provenance["provenance.jsonl<br/>pipeline events"]
    Bundle --> Raw["raw/<br/>provider payloads and PDFs"]
    Bundle --> Notes["notes/<br/>per-source notes"]

    Manifest -. "schema checked by inspect" .-> Request
    Manifest -. "schema checked by inspect" .-> Queries
    Manifest -. "schema checked by inspect" .-> Sources
    Manifest -. "schema checked by inspect" .-> Triage
    Manifest -. "schema checked by inspect" .-> Evidence
```

## Module Map

```mermaid
flowchart TB
    subgraph Entry["Entry Points"]
        CLIFile["cli.py"]
        MainFile["__main__.py"]
        InitFile["__init__.py"]
    end

    subgraph Core["Core Pipeline"]
        PipelineFile["pipeline.py"]
        ModelsFile["models.py"]
        ConfigFile["config.py"]
        PlannerFile["query_planner.py"]
        DedupeFile["dedupe.py"]
        RankingFile["ranking.py"]
        EvidenceFile2["evidence.py"]
        BriefFile["brief.py"]
        BibFile["bibtex.py"]
        BundleFile["bundle.py"]
        UtilsFile["utils.py"]
    end

    subgraph Integrations["Integrations"]
        ProviderBase["providers/base.py"]
        ProviderFiles["providers/*.py"]
        LLMFile["llm/openai_compatible.py"]
        PDFFile["readers/pdf.py"]
    end

    subgraph Product["Product Surface"]
        RootSkillFile["SKILL.md"]
        Docs["docs/"]
        Examples["examples/"]
        Tests["tests/"]
    end

    CLIFile --> PipelineFile
    InitFile --> PipelineFile
    PipelineFile --> ModelsFile
    PipelineFile --> ConfigFile
    PipelineFile --> PlannerFile
    PipelineFile --> ProviderFiles
    PipelineFile --> DedupeFile
    PipelineFile --> RankingFile
    PipelineFile --> EvidenceFile2
    PipelineFile --> BriefFile
    PipelineFile --> BibFile
    PipelineFile --> BundleFile
    ProviderFiles --> ProviderBase
    BriefFile --> LLMFile
    PipelineFile --> LLMFile
    PipelineFile --> PDFFile
    Tests --> Core
    RootSkillFile --> CLIFile
    Docs --> BundleFile
```
