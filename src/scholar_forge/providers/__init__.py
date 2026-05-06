from __future__ import annotations

from .arxiv import ArxivProvider
from .base import ProviderStatus, SearchProvider
from .openalex import OpenAlexProvider
from .pubmed import PubMedProvider
from .semantic_scholar import SemanticScholarProvider
from .tavily import TavilyProvider


def provider_registry() -> dict[str, SearchProvider]:
    providers = [
        TavilyProvider(),
        SemanticScholarProvider(),
        OpenAlexProvider(),
        PubMedProvider(),
        ArxivProvider(),
    ]
    return {provider.name: provider for provider in providers}


__all__ = ["ProviderStatus", "SearchProvider", "provider_registry"]

