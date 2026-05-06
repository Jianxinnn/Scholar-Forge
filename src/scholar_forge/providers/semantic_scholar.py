from __future__ import annotations

from typing import Any

import httpx

from scholar_forge.config import ScholarForgeConfig
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.providers.base import ProviderStatus
from scholar_forge.utils import safe_id


class SemanticScholarProvider:
    name = "semantic_scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = ",".join(
        [
            "paperId",
            "corpusId",
            "url",
            "title",
            "abstract",
            "authors",
            "year",
            "venue",
            "citationCount",
            "openAccessPdf",
            "externalIds",
            "isOpenAccess",
            "fieldsOfStudy",
            "tldr",
        ]
    )

    def status(self, config: ScholarForgeConfig) -> ProviderStatus:
        enabled = config.provider_enabled(self.name)
        key = config.provider_api_key(self.name)
        detail = "S2_API_KEY configured" if key else "S2_API_KEY optional but recommended"
        return ProviderStatus(self.name, enabled, True, detail)

    def fetch(
        self,
        query: QueryRecord,
        request: ResearchRequest,
        config: ScholarForgeConfig,
        *,
        limit: int,
    ) -> Any:
        params: dict[str, Any] = {"query": query.query, "limit": min(limit, 100), "fields": self.fields}
        if request.year_range:
            params["year"] = request.year_range
        headers = {}
        key = config.provider_api_key(self.name)
        if key:
            headers["x-api-key"] = key
        with httpx.Client(timeout=30, trust_env=False) as client:
            resp = client.get(self.endpoint, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for paper in (raw or {}).get("data", []):
            ext = paper.get("externalIds") or {}
            pdf = paper.get("openAccessPdf") or {}
            authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
            tldr = paper.get("tldr") or {}
            tldr_text = tldr.get("text") if isinstance(tldr, dict) else ""
            paper_id = paper.get("paperId", "")
            title = paper.get("title", "")
            records.append(
                SourceRecord(
                    source_id=safe_id("src", "s2", paper_id, ext.get("DOI", ""), title),
                    title=title,
                    abstract=paper.get("abstract") or "",
                    snippet=tldr_text or "",
                    authors=authors,
                    year=paper.get("year"),
                    venue=paper.get("venue") or "",
                    doi=ext.get("DOI", ""),
                    arxiv_id=ext.get("ArXiv", ""),
                    pubmed_id=ext.get("PubMed", ""),
                    semantic_scholar_id=paper_id,
                    url=paper.get("url", ""),
                    pdf_url=pdf.get("url", "") if isinstance(pdf, dict) else "",
                    provider=self.name,
                    citation_count=paper.get("citationCount"),
                    fields=list(paper.get("fieldsOfStudy") or []),
                    raw={"query": query.query, "tldr": tldr_text, "corpusId": paper.get("corpusId")},
                )
            )
        return records
