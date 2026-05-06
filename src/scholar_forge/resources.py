from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import ResearchRequest, ResourceRecord, SourceRecord
from .utils import safe_id


RESOURCE_KINDS = {
    "paper",
    "web_page",
    "full_text",
    "pdf",
    "structure",
    "sequence",
    "dataset",
    "code",
    "protocol",
    "patent",
    "other",
}

PDB_ID_RE = re.compile(r"\b(?=[0-9A-Za-z]{4}\b)(?=[0-9A-Za-z]*[A-Za-z])([0-9][0-9A-Za-z]{3})\b")
PDB_PREFIX_RE = re.compile(
    r"\b(?:PDB(?:\s+(?:ID|entry|structure))?|RCSB)\s*[:#-]?\s*([0-9][0-9A-Za-z]{3})\b",
    re.IGNORECASE,
)
PDB_CONTEXT_RE = re.compile(
    r"\b("
    r"pdb|rcsb|protein data bank|mmcif|cif|crystal structure|cryo-?em|"
    r"structure of|structural basis|x-ray|xray"
    r")\b",
    re.IGNORECASE,
)

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def _canonical_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    query_items = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    path = parsed.path
    if path != "/":
        path = path.rstrip("/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query_items, doseq=True),
            "",
        )
    )


def _normalize_doi(doi: str) -> str:
    value = doi.strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.strip().lower()


def _add_identifier(record: ResourceRecord, key: str, value: str) -> None:
    if not value:
        return
    values = record.identifiers.setdefault(key, [])
    if value not in values:
        values.append(value)


def _add_access(record: ResourceRecord, kind: str, url: str, source: str) -> None:
    if not url:
        return
    item = {"kind": kind, "url": _canonical_url(url), "source": source}
    if item not in record.access:
        record.access.append(item)


def _merge_record(existing: ResourceRecord, incoming: ResourceRecord) -> ResourceRecord:
    for source_id in incoming.source_ids:
        if source_id and source_id not in existing.source_ids:
            existing.source_ids.append(source_id)
    for provider in incoming.providers:
        if provider and provider not in existing.providers:
            existing.providers.append(provider)
    for key, values in incoming.identifiers.items():
        for value in values:
            _add_identifier(existing, key, value)
    for item in incoming.access:
        if item not in existing.access:
            existing.access.append(item)
    if not existing.title and incoming.title:
        existing.title = incoming.title
    if not existing.url and incoming.url:
        existing.url = incoming.url
    existing.confidence = max(existing.confidence, incoming.confidence)
    if incoming.reason and incoming.reason not in existing.reason:
        existing.reason = f"{existing.reason}; {incoming.reason}".strip("; ")
    return existing


def _resource(
    *,
    resource_id: str,
    resource_kind: str,
    source: SourceRecord,
    title: str,
    url: str,
    confidence: float,
    reason: str,
) -> ResourceRecord:
    return ResourceRecord(
        resource_id=resource_id,
        resource_kind=resource_kind if resource_kind in RESOURCE_KINDS else "other",
        source_ids=[source.source_id] if source.source_id else [],
        title=title,
        url=_canonical_url(url),
        providers=[source.provider] if source.provider else [],
        status="candidate",
        confidence=confidence,
        reason=reason,
    )


def _pdb_id_from_structure_url(url: str) -> str:
    parsed = urlparse(url)
    text = f"{parsed.netloc}{parsed.path}"
    patterns = [
        r"rcsb\.org/structure/([0-9][0-9A-Za-z]{3})\b",
        r"files\.rcsb\.org/download/([0-9][0-9A-Za-z]{3})\.(?:cif|pdb|bcif)\b",
        r"pdbj\.org/.*/([0-9][0-9A-Za-z]{3})\b",
        r"ebi\.ac\.uk/pdbe/entry/pdb/([0-9][0-9A-Za-z]{3})\b",
        r"ncbi\.nlm\.nih\.gov/Structure/pdb/([0-9][0-9A-Za-z]{3})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return ""


def _structure_resource(source: SourceRecord, pdb_id: str, *, matched_url: str = "", reason: str) -> ResourceRecord:
    pdb_id = pdb_id.upper()
    rcsb_url = f"https://www.rcsb.org/structure/{pdb_id}"
    record = _resource(
        resource_id=f"res_pdb_{pdb_id.lower()}",
        resource_kind="structure",
        source=source,
        title=f"PDB {pdb_id}",
        url=rcsb_url,
        confidence=0.95 if matched_url else 0.8,
        reason=reason,
    )
    _add_identifier(record, "pdb_ids", pdb_id)
    if matched_url:
        _add_access(record, "landing_page", matched_url, "provider")
    _add_access(record, "rcsb_landing_page", rcsb_url, "provider" if _canonical_url(matched_url) == rcsb_url else "derived")
    _add_access(record, "mmcif", f"https://files.rcsb.org/download/{pdb_id}.cif", "derived")
    _add_access(record, "pdb", f"https://files.rcsb.org/download/{pdb_id}.pdb", "derived")
    return record


def _pdb_ids_from_text(source: SourceRecord, request: ResearchRequest) -> list[str]:
    text = " ".join([source.title, source.abstract, source.snippet])
    if not text:
        return []
    ids: list[str] = []
    for match in PDB_PREFIX_RE.finditer(text):
        pdb_id = match.group(1).upper()
        if pdb_id not in ids:
            ids.append(pdb_id)
    strong_context = bool(PDB_CONTEXT_RE.search(text))
    if not strong_context:
        return ids
    for match in PDB_ID_RE.finditer(text):
        start = match.start(1)
        if start > 0 and text[start - 1] == "-":
            continue
        pdb_id = match.group(1).upper()
        if re.fullmatch(r"[0-9]{1,2}(ST|ND|RD|TH)", pdb_id):
            continue
        if pdb_id not in ids:
            ids.append(pdb_id)
    return ids


def _source_url_resource(source: SourceRecord) -> ResourceRecord | None:
    url = _canonical_url(source.url)
    if not url:
        return None
    if _pdb_id_from_structure_url(url):
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    title = source.title or url

    if "uniprot.org" in host:
        record = _resource(
            resource_id=safe_id("res", "sequence", url),
            resource_kind="sequence",
            source=source,
            title=title,
            url=url,
            confidence=0.9,
            reason="Matched UniProt URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if "pmc.ncbi.nlm.nih.gov" in host or "/pmc/" in path:
        record = _resource(
            resource_id=safe_id("res", "full_text", url),
            resource_kind="full_text",
            source=source,
            title=title,
            url=url,
            confidence=0.85,
            reason="Matched full-text URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if "github.com" in host or "gitlab.com" in host:
        record = _resource(
            resource_id=safe_id("res", "code", url),
            resource_kind="code",
            source=source,
            title=title,
            url=url,
            confidence=0.85,
            reason="Matched code repository URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if any(domain in host for domain in ["zenodo.org", "figshare.com", "kaggle.com", "huggingface.co"]):
        record = _resource(
            resource_id=safe_id("res", "dataset", url),
            resource_kind="dataset",
            source=source,
            title=title,
            url=url,
            confidence=0.8,
            reason="Matched dataset host URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if "protocols.io" in host:
        record = _resource(
            resource_id=safe_id("res", "protocol", url),
            resource_kind="protocol",
            source=source,
            title=title,
            url=url,
            confidence=0.85,
            reason="Matched protocol URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if "patents.google.com" in host or "/patent/" in path:
        record = _resource(
            resource_id=safe_id("res", "patent", url),
            resource_kind="patent",
            source=source,
            title=title,
            url=url,
            confidence=0.8,
            reason="Matched patent URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if "pubmed.ncbi.nlm.nih.gov" in host or "doi.org" in host or "arxiv.org" in host:
        record = _resource(
            resource_id=safe_id("res", "paper", url),
            resource_kind="paper",
            source=source,
            title=title,
            url=url,
            confidence=0.75,
            reason="Matched paper landing URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if source.source_type == "web":
        record = _resource(
            resource_id=safe_id("res", "web_page", url),
            resource_kind="web_page",
            source=source,
            title=title,
            url=url,
            confidence=0.55,
            reason="Captured web search result URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    if source.source_type == "paper":
        record = _resource(
            resource_id=safe_id("res", "paper", url),
            resource_kind="paper",
            source=source,
            title=title,
            url=url,
            confidence=0.65,
            reason="Captured paper source URL.",
        )
        _add_access(record, "landing_page", url, "provider")
        return record
    return None


def _identifier_resources(source: SourceRecord) -> list[ResourceRecord]:
    records: list[ResourceRecord] = []
    if source.doi:
        doi = _normalize_doi(source.doi)
        url = f"https://doi.org/{doi}"
        record = _resource(
            resource_id=safe_id("res", "doi", doi),
            resource_kind="paper",
            source=source,
            title=source.title or doi,
            url=url,
            confidence=0.8,
            reason="Source DOI identifier.",
        )
        _add_identifier(record, "dois", doi)
        _add_access(record, "doi", url, "derived")
        records.append(record)
    if source.pubmed_id:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{source.pubmed_id}/"
        record = _resource(
            resource_id=f"res_pubmed_{source.pubmed_id}",
            resource_kind="paper",
            source=source,
            title=source.title or f"PubMed {source.pubmed_id}",
            url=url,
            confidence=0.8,
            reason="Source PubMed identifier.",
        )
        _add_identifier(record, "pubmed_ids", source.pubmed_id)
        _add_access(record, "landing_page", url, "derived")
        records.append(record)
    if source.arxiv_id:
        arxiv_id = source.arxiv_id
        url = f"https://arxiv.org/abs/{arxiv_id}"
        record = _resource(
            resource_id=safe_id("res", "arxiv", arxiv_id),
            resource_kind="paper",
            source=source,
            title=source.title or f"arXiv {arxiv_id}",
            url=url,
            confidence=0.8,
            reason="Source arXiv identifier.",
        )
        _add_identifier(record, "arxiv_ids", arxiv_id)
        _add_access(record, "landing_page", url, "derived")
        _add_access(record, "pdf", f"https://arxiv.org/pdf/{arxiv_id}", "derived")
        records.append(record)
    return records


def _pdf_resource(source: SourceRecord) -> ResourceRecord | None:
    url = _canonical_url(source.pdf_url)
    if not url:
        return None
    record = _resource(
        resource_id=safe_id("res", "pdf", url),
        resource_kind="pdf",
        source=source,
        title=source.title or url,
        url=url,
        confidence=0.8,
        reason="Source PDF URL.",
    )
    _add_access(record, "pdf", url, "provider")
    return record


def extract_resources(request: ResearchRequest, sources: list[SourceRecord]) -> list[ResourceRecord]:
    by_key: dict[tuple[str, str], ResourceRecord] = {}

    def add(key: tuple[str, str], record: ResourceRecord | None) -> None:
        if record is None:
            return
        existing = by_key.get(key)
        if existing:
            _merge_record(existing, record)
        else:
            by_key[key] = record

    for source in sources:
        url = _canonical_url(source.url)
        pdb_id = _pdb_id_from_structure_url(url)
        if pdb_id:
            add(
                ("structure", pdb_id),
                _structure_resource(source, pdb_id, matched_url=url, reason="Matched structure database URL."),
            )

        for pdb_id in _pdb_ids_from_text(source, request):
            add(
                ("structure", pdb_id),
                _structure_resource(source, pdb_id, reason="Matched PDB ID in structure-related title/snippet context."),
            )

        url_resource = _source_url_resource(source)
        if url_resource and url_resource.resource_kind != "structure":
            add((url_resource.resource_kind, url_resource.url), url_resource)

        pdf = _pdf_resource(source)
        if pdf:
            add(("pdf", pdf.url), pdf)

        for record in _identifier_resources(source):
            identifier_key = next(iter(record.identifiers.values()), [record.url])[0]
            add((record.resource_kind, identifier_key), record)

    return sorted(
        by_key.values(),
        key=lambda record: (-record.confidence, record.resource_kind, record.title.lower(), record.url),
    )
