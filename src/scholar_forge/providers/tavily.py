from __future__ import annotations

from typing import Any

import httpx

from scholar_forge.config import ScholarForgeConfig
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.providers.base import ProviderError, ProviderStatus
from scholar_forge.utils import safe_id


class TavilyProvider:
    name = "tavily"
    default_endpoint = "https://api.tavily.com/search"

    def status(self, config: ScholarForgeConfig) -> ProviderStatus:
        enabled = config.provider_enabled(self.name)
        key = config.provider_api_key(self.name)
        return ProviderStatus(self.name, enabled, bool(key), "TAVILY_API_KEY configured" if key else "missing TAVILY_API_KEY")

    def fetch(
        self,
        query: QueryRecord,
        request: ResearchRequest,
        config: ScholarForgeConfig,
        *,
        limit: int,
    ) -> Any:
        key = config.provider_api_key(self.name)
        if not key:
            raise ProviderError("Tavily requires TAVILY_API_KEY")
        payload = {
            "api_key": key,
            "query": query.query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": limit,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "use_cache": True,
        }
        endpoint = config.provider_config(self.name).get("base_url") or self.default_endpoint
        with httpx.Client(timeout=30, trust_env=False) as client:
            resp = client.post(str(endpoint), json=payload)
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for item in (raw or {}).get("results", []):
            url = item.get("url", "")
            title = item.get("title") or url
            content = item.get("content", "")
            records.append(
                SourceRecord(
                    source_id=safe_id("src", self.name, url, title),
                    title=title,
                    source_type="web",
                    snippet=content,
                    url=url,
                    provider=self.name,
                    raw={"score": item.get("score"), "query": query.query},
                )
            )
        return records
