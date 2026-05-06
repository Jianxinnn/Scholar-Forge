from __future__ import annotations

from typing import Any
import time
from xml.etree import ElementTree

import httpx

from scholar_forge.config import ScholarForgeConfig
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.providers.base import ProviderStatus
from scholar_forge.utils import safe_id


ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


class ArxivProvider:
    name = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"

    def status(self, config: ScholarForgeConfig) -> ProviderStatus:
        return ProviderStatus(self.name, config.provider_enabled(self.name), True, "no API key required")

    def fetch(
        self,
        query: QueryRecord,
        request: ResearchRequest,
        config: ScholarForgeConfig,
        *,
        limit: int,
    ) -> Any:
        params = {
            "search_query": f"all:{query.query}",
            "start": 0,
            "max_results": min(limit, 100),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        last_error: Exception | None = None
        with httpx.Client(timeout=30, trust_env=False) as client:
            for attempt in range(3):
                try:
                    resp = client.get(self.endpoint, params=params)
                    if resp.status_code == 429 and attempt < 2:
                        time.sleep(3 + attempt * 3)
                        continue
                    resp.raise_for_status()
                    return {"entries": self._parse(resp.text), "query": query.query}
                except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                    last_error = exc
                    if attempt < 2:
                        time.sleep(2 + attempt * 3)
                        continue
                    raise
        raise last_error or RuntimeError("arXiv request failed")

    def _parse(self, xml_text: str) -> list[dict[str, Any]]:
        root = ElementTree.fromstring(xml_text)
        entries: list[dict[str, Any]] = []
        for entry in root.findall(f"{ATOM}entry"):
            arxiv_url = (entry.findtext(f"{ATOM}id") or "").strip()
            arxiv_id = arxiv_url.rstrip("/").split("/")[-1]
            pdf_url = ""
            for link in entry.findall(f"{ATOM}link"):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href", "")
                    break
            authors = [
                (author.findtext(f"{ATOM}name") or "").strip()
                for author in entry.findall(f"{ATOM}author")
                if (author.findtext(f"{ATOM}name") or "").strip()
            ]
            year = None
            published = entry.findtext(f"{ATOM}published") or ""
            if len(published) >= 4 and published[:4].isdigit():
                year = int(published[:4])
            entries.append(
                {
                    "arxiv_id": arxiv_id,
                    "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
                    "abstract": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
                    "authors": authors,
                    "year": year,
                    "url": arxiv_url,
                    "pdf_url": pdf_url,
                    "categories": [c.attrib.get("term", "") for c in entry.findall(f"{ATOM}category")],
                    "doi": entry.findtext(f"{ARXIV}doi") or "",
                }
            )
        return entries

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for item in (raw or {}).get("entries", []):
            title = item.get("title", "")
            arxiv_id = item.get("arxiv_id", "")
            records.append(
                SourceRecord(
                    source_id=safe_id("src", "arxiv", arxiv_id, title),
                    title=title,
                    abstract=item.get("abstract", ""),
                    authors=list(item.get("authors") or []),
                    year=item.get("year"),
                    venue="arXiv",
                    doi=item.get("doi", ""),
                    arxiv_id=arxiv_id,
                    url=item.get("url", ""),
                    pdf_url=item.get("pdf_url", ""),
                    provider=self.name,
                    fields=list(item.get("categories") or []),
                    raw={"query": query.query},
                )
            )
        return records
