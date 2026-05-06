from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from scholar_forge.config import ScholarForgeConfig
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord


class ProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class ProviderStatus:
    name: str
    enabled: bool
    available: bool
    detail: str = ""


class SearchProvider(Protocol):
    name: str

    def status(self, config: ScholarForgeConfig) -> ProviderStatus: ...

    def fetch(
        self,
        query: QueryRecord,
        request: ResearchRequest,
        config: ScholarForgeConfig,
        *,
        limit: int,
    ) -> Any: ...

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]: ...

