from __future__ import annotations

from scholar_forge.models import QueryRecord, ResearchRequest
from scholar_forge.providers.arxiv import ArxivProvider
from scholar_forge.providers.openalex import OpenAlexProvider
from scholar_forge.providers.pubmed import PubMedProvider
from scholar_forge.providers.semantic_scholar import SemanticScholarProvider
from scholar_forge.providers.tavily import TavilyProvider


QUERY = QueryRecord(query="protein design")
REQUEST = ResearchRequest(question="protein design")


def test_semantic_scholar_normalize() -> None:
    raw = {
        "data": [
            {
                "paperId": "abc",
                "title": "Protein design paper",
                "abstract": "Abstract text",
                "authors": [{"name": "Ada Lovelace"}],
                "year": 2024,
                "venue": "Nature",
                "citationCount": 10,
                "externalIds": {"DOI": "10.1/test", "ArXiv": "2401.1"},
                "openAccessPdf": {"url": "https://example.test/a.pdf"},
                "fieldsOfStudy": ["Biology"],
                "tldr": {"text": "Short summary"},
            }
        ]
    }
    records = SemanticScholarProvider().normalize(raw, QUERY, REQUEST)
    assert records[0].semantic_scholar_id == "abc"
    assert records[0].doi == "10.1/test"
    assert records[0].pdf_url


def test_tavily_normalize() -> None:
    raw = {"results": [{"title": "A page", "url": "https://example.test", "content": "Snippet", "score": 0.8}]}
    records = TavilyProvider().normalize(raw, QUERY, REQUEST)
    assert records[0].source_type == "web"
    assert records[0].snippet == "Snippet"


def test_openalex_normalize_reconstructs_abstract() -> None:
    raw = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.2/test",
                "title": "OpenAlex Paper",
                "publication_year": 2023,
                "abstract_inverted_index": {"hello": [0], "world": [1]},
                "authorships": [{"author": {"display_name": "Grace Hopper"}}],
                "primary_location": {"landing_page_url": "https://paper.test", "source": {"display_name": "Journal"}},
                "open_access": {"oa_url": "https://paper.test/pdf"},
                "cited_by_count": 5,
                "concepts": [{"display_name": "Biology"}],
            }
        ]
    }
    records = OpenAlexProvider().normalize(raw, QUERY, REQUEST)
    assert records[0].abstract == "hello world"
    assert records[0].doi == "10.2/test"


def test_pubmed_normalize() -> None:
    raw = {
        "articles": [
            {
                "pmid": "123",
                "title": "PubMed Paper",
                "abstract": "Medical abstract",
                "authors": ["A B"],
                "year": 2022,
                "venue": "Journal",
                "doi": "10.3/test",
            }
        ]
    }
    records = PubMedProvider().normalize(raw, QUERY, REQUEST)
    assert records[0].pubmed_id == "123"
    assert records[0].url.endswith("/123/")


def test_arxiv_normalize() -> None:
    raw = {
        "entries": [
            {
                "arxiv_id": "2401.00001",
                "title": "arXiv Paper",
                "abstract": "Arxiv abstract",
                "authors": ["A B"],
                "year": 2024,
                "url": "https://arxiv.org/abs/2401.00001",
                "pdf_url": "https://arxiv.org/pdf/2401.00001",
                "categories": ["cs.LG"],
            }
        ]
    }
    records = ArxivProvider().normalize(raw, QUERY, REQUEST)
    assert records[0].arxiv_id == "2401.00001"
    assert records[0].venue == "arXiv"

