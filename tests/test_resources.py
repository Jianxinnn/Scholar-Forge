from __future__ import annotations

from typing import Any

from scholar_forge.bundle import read_jsonl
from scholar_forge.config import load_config
from scholar_forge.models import QueryRecord, ResearchRequest, SourceRecord
from scholar_forge.pipeline import ScholarPipeline
from scholar_forge.providers.base import ProviderStatus
from scholar_forge.resources import extract_resources


def test_extract_resources_detects_rcsb_structure_url() -> None:
    source = SourceRecord(
        source_id="src_rcsb",
        title="5J13: Structural basis for TSLP antagonism",
        source_type="web",
        url="https://www.rcsb.org/structure/5j13",
        provider="tavily",
    )

    resources = extract_resources(ResearchRequest(question="TSLP PDB", profile="biomol"), [source])
    structure = next(resource for resource in resources if resource.resource_kind == "structure")

    assert structure.resource_id == "res_pdb_5j13"
    assert structure.identifiers["pdb_ids"] == ["5J13"]
    assert structure.source_ids == ["src_rcsb"]
    assert structure.status == "candidate"
    assert any(item["kind"] == "mmcif" and item["source"] == "derived" for item in structure.access)
    assert any(item["url"] == "https://files.rcsb.org/download/5J13.pdb" for item in structure.access)


def test_extract_resources_detects_bare_pdb_id_only_with_structure_context() -> None:
    structured = SourceRecord(
        source_id="src_text",
        title="Structure of human TSLP in complex with TSLPR and IL-7Ralpha 5J11",
        provider="tavily",
    )
    unrelated = SourceRecord(source_id="src_noise", title="A 5J11 label without context", provider="tavily")

    resources = extract_resources(ResearchRequest(question="TSLP", profile="biomol"), [structured, unrelated])

    assert [resource.resource_id for resource in resources if resource.resource_kind == "structure"] == [
        "res_pdb_5j11"
    ]


def test_extract_resources_merges_same_pdb_id_across_sources() -> None:
    first = SourceRecord(
        source_id="src_a",
        title="5J13: Structural basis for TSLP antagonism",
        source_type="web",
        url="https://www.rcsb.org/structure/5J13",
        provider="tavily",
    )
    second = SourceRecord(
        source_id="src_b",
        title="PDB 5J13 TSLP antibody complex",
        provider="pubmed",
    )

    resources = extract_resources(ResearchRequest(question="TSLP", profile="biomol"), [first, second])
    structure = next(resource for resource in resources if resource.resource_id == "res_pdb_5j13")

    assert structure.source_ids == ["src_a", "src_b"]
    assert sorted(structure.providers) == ["pubmed", "tavily"]


class FakeResourceProvider:
    name = "fake_resource"

    def status(self, config) -> ProviderStatus:
        return ProviderStatus(self.name, True, True, "fixture")

    def fetch(self, query: QueryRecord, request: ResearchRequest, config, *, limit: int) -> Any:
        return {"results": [{"title": "unused"}]}

    def normalize(self, raw: Any, query: QueryRecord, request: ResearchRequest) -> list[SourceRecord]:
        return [
            SourceRecord(
                source_id="src_rcsb",
                title="5J13: Structural basis for TSLP antagonism",
                source_type="web",
                url="https://www.rcsb.org/structure/5J13",
                provider=self.name,
            )
        ]


def test_pipeline_resources_are_independent_of_triage_decision(tmp_path) -> None:
    out = tmp_path / "bundle"
    pipeline = ScholarPipeline(load_config())
    pipeline.providers["fake_resource"] = FakeResourceProvider()
    request = ResearchRequest(
        question="unrelated classroom survey",
        profile="biomol",
        providers=["fake_resource"],
        max_papers=1,
        use_llm=False,
    )

    pipeline.run(request, out=out)

    triage = read_jsonl(out / "triage.jsonl")
    resources = read_jsonl(out / "resources.jsonl")
    assert triage[0]["decision"] == "exclude"
    assert any(resource["resource_id"] == "res_pdb_5j13" for resource in resources)
