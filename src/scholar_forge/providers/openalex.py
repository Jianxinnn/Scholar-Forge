from __future__ import annotations

from typing import Any

import httpx

from scholar_forge.config import ScholarForgeConfig
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.providers.base import ProviderStatus
from scholar_forge.utils import safe_id


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        for pos in positions:
            positioned.append((pos, word))
    return " ".join(word for _, word in sorted(positioned))


class OpenAlexProvider:
    name = "openalex"
    endpoint = "https://api.openalex.org/works"

    def status(self, config: ScholarForgeConfig) -> ProviderStatus:
        enabled = config.provider_enabled(self.name)
        email = config.provider_email(self.name)
        detail = "OPENALEX_EMAIL configured" if email else "OPENALEX_EMAIL optional but recommended"
        return ProviderStatus(self.name, enabled, True, detail)

    def fetch(
        self,
        query: QueryRecord,
        request: ResearchRequest,
        config: ScholarForgeConfig,
        *,
        limit: int,
    ) -> Any:
        params: dict[str, Any] = {"search": query.query, "per-page": min(limit, 200)}
        email = config.provider_email(self.name)
        if email:
            params["mailto"] = email
        if request.year_range and request.year_range.endswith("-"):
            start = request.year_range[:-1]
            if start.isdigit():
                params["filter"] = f"from_publication_date:{start}-01-01"
        with httpx.Client(timeout=30, trust_env=False) as client:
            resp = client.get(self.endpoint, params=params)
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for item in (raw or {}).get("results", []):
            primary = item.get("primary_location") or {}
            source = primary.get("source") or {}
            open_access = item.get("open_access") or {}
            doi = (item.get("doi") or "").removeprefix("https://doi.org/")
            authors = [
                (auth.get("author") or {}).get("display_name", "")
                for auth in item.get("authorships", [])
                if (auth.get("author") or {}).get("display_name")
            ]
            concepts = [c.get("display_name", "") for c in item.get("concepts", []) if c.get("display_name")]
            title = item.get("title") or item.get("display_name") or ""
            records.append(
                SourceRecord(
                    source_id=safe_id("src", "openalex", item.get("id", ""), doi, title),
                    title=title,
                    abstract=_abstract_from_inverted_index(item.get("abstract_inverted_index")),
                    authors=authors,
                    year=item.get("publication_year"),
                    venue=source.get("display_name", "") if isinstance(source, dict) else "",
                    doi=doi,
                    openalex_id=item.get("id", ""),
                    url=primary.get("landing_page_url") or item.get("id", ""),
                    pdf_url=open_access.get("oa_url", "") if isinstance(open_access, dict) else "",
                    provider=self.name,
                    citation_count=item.get("cited_by_count"),
                    fields=concepts,
                    raw={"query": query.query},
                )
            )
        return records
