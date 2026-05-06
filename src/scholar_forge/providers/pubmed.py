from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

import httpx

from scholar_forge.config import ScholarForgeConfig
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.providers.base import ProviderStatus
from scholar_forge.utils import safe_id


def _text(el: ElementTree.Element | None) -> str:
    if el is None:
        return ""
    return " ".join(t.strip() for t in el.itertext() if t and t.strip())


class PubMedProvider:
    name = "pubmed"
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def status(self, config: ScholarForgeConfig) -> ProviderStatus:
        enabled = config.provider_enabled(self.name)
        email = config.provider_email(self.name)
        key = config.provider_api_key(self.name)
        detail = "NCBI email/key configured" if email or key else "NCBI_EMAIL optional but recommended"
        return ProviderStatus(self.name, enabled, True, detail)

    def fetch(
        self,
        query: QueryRecord,
        request: ResearchRequest,
        config: ScholarForgeConfig,
        *,
        limit: int,
    ) -> Any:
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": query.query,
            "retmax": min(limit, 100),
            "retmode": "json",
            "sort": "relevance",
            "tool": "ScholarForge",
        }
        email = config.provider_email(self.name)
        key = config.provider_api_key(self.name)
        if email:
            params["email"] = email
        if key:
            params["api_key"] = key
        with httpx.Client(timeout=30, trust_env=False) as client:
            search_resp = client.get(f"{self.base}/esearch.fcgi", params=params)
            search_resp.raise_for_status()
            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return {"ids": [], "articles": []}
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
                "tool": "ScholarForge",
            }
            if email:
                fetch_params["email"] = email
            if key:
                fetch_params["api_key"] = key
            fetch_resp = client.get(f"{self.base}/efetch.fcgi", params=fetch_params)
            fetch_resp.raise_for_status()
            return {"ids": ids, "articles": self._parse_articles(fetch_resp.text), "query": query.query}

    def _parse_articles(self, xml_text: str) -> list[dict[str, Any]]:
        root = ElementTree.fromstring(xml_text)
        articles: list[dict[str, Any]] = []
        for pubmed_article in root.findall("./PubmedArticle"):
            article = pubmed_article.find(".//Article")
            if article is None:
                continue
            pmid = _text(pubmed_article.find(".//PMID"))
            title = _text(article.find(".//ArticleTitle"))
            abstract_parts = []
            for ab_text in article.findall(".//Abstract/AbstractText"):
                label = ab_text.attrib.get("Label")
                text = _text(ab_text)
                if label and text:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
            authors = []
            for author in article.findall(".//Author"):
                last = _text(author.find("./LastName"))
                first = _text(author.find("./ForeName"))
                if last or first:
                    authors.append(" ".join(p for p in [first, last] if p))
            year_text = _text(article.find(".//Journal/JournalIssue/PubDate/Year"))
            doi = ""
            for aid in pubmed_article.findall(".//ArticleId"):
                if aid.attrib.get("IdType") == "doi":
                    doi = _text(aid)
                    break
            articles.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "abstract": " ".join(abstract_parts),
                    "authors": authors,
                    "year": int(year_text) if year_text.isdigit() else None,
                    "venue": _text(article.find(".//Journal/Title")),
                    "doi": doi,
                }
            )
        return articles

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for article in (raw or {}).get("articles", []):
            pmid = article.get("pmid", "")
            title = article.get("title", "")
            records.append(
                SourceRecord(
                    source_id=safe_id("src", "pubmed", pmid, article.get("doi", ""), title),
                    title=title,
                    abstract=article.get("abstract", ""),
                    authors=list(article.get("authors") or []),
                    year=article.get("year"),
                    venue=article.get("venue", ""),
                    doi=article.get("doi", ""),
                    pubmed_id=pmid,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    provider=self.name,
                    fields=["Medicine", "Biology"],
                    raw={"query": query.query},
                )
            )
        return records
