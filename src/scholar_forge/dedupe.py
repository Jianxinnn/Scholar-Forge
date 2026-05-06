from __future__ import annotations

from .models import SourceRecord
from .utils import title_fingerprint


def source_identity_keys(source: SourceRecord) -> list[str]:
    keys: list[str] = []
    if source.doi:
        keys.append(f"doi:{source.doi.lower().removeprefix('https://doi.org/')}")
    if source.semantic_scholar_id:
        keys.append(f"s2:{source.semantic_scholar_id}")
    if source.openalex_id:
        keys.append(f"openalex:{source.openalex_id}")
    if source.pubmed_id:
        keys.append(f"pubmed:{source.pubmed_id}")
    if source.arxiv_id:
        keys.append(f"arxiv:{source.arxiv_id.lower()}")
    fp = title_fingerprint(source.title)
    if fp:
        keys.append(f"title:{fp}")
    return keys


def _merge_source(existing: SourceRecord, incoming: SourceRecord) -> SourceRecord:
    if incoming.abstract and not existing.abstract:
        existing.abstract = incoming.abstract
    if incoming.snippet and not existing.snippet:
        existing.snippet = incoming.snippet
    if incoming.pdf_url and not existing.pdf_url:
        existing.pdf_url = incoming.pdf_url
    if incoming.url and not existing.url:
        existing.url = incoming.url
    if incoming.doi and not existing.doi:
        existing.doi = incoming.doi
    if incoming.arxiv_id and not existing.arxiv_id:
        existing.arxiv_id = incoming.arxiv_id
    if incoming.pubmed_id and not existing.pubmed_id:
        existing.pubmed_id = incoming.pubmed_id
    if incoming.semantic_scholar_id and not existing.semantic_scholar_id:
        existing.semantic_scholar_id = incoming.semantic_scholar_id
    if incoming.openalex_id and not existing.openalex_id:
        existing.openalex_id = incoming.openalex_id
    if incoming.citation_count is not None:
        if existing.citation_count is None or incoming.citation_count > existing.citation_count:
            existing.citation_count = incoming.citation_count
    for author in incoming.authors:
        if author not in existing.authors:
            existing.authors.append(author)
    for field in incoming.fields:
        if field not in existing.fields:
            existing.fields.append(field)
    providers = set(existing.raw.get("providers_seen") or [existing.provider])
    providers.add(incoming.provider)
    existing.raw["providers_seen"] = sorted(p for p in providers if p)
    return existing


def dedupe_sources(sources: list[SourceRecord]) -> list[SourceRecord]:
    identity_to_source: dict[str, SourceRecord] = {}
    deduped: list[SourceRecord] = []

    for source in sources:
        keys = source_identity_keys(source)
        existing = next((identity_to_source[k] for k in keys if k in identity_to_source), None)
        if existing is None:
            source.raw.setdefault("providers_seen", [source.provider] if source.provider else [])
            deduped.append(source)
            for key in keys:
                identity_to_source[key] = source
        else:
            _merge_source(existing, source)
            for key in keys:
                identity_to_source[key] = existing

    return deduped

