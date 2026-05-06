from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .bibtex import write_references
from .brief import append_resource_index, build_llm_brief_prompt, write_brief
from .bundle import BundleWriter, load_request
from .config import ScholarForgeConfig, load_config
from .dedupe import dedupe_sources
from .evidence import extract_evidence, note_for_source
from .models import QueryRecord, ResearchRequest, SourceRecord, TriageRecord
from .providers import provider_registry
from .providers.base import SearchProvider
from .query_planner import plan_queries
from .ranking import rank_sources
from .resources import extract_resources
from .utils import read_json, utc_now_iso

ProgressCallback = Callable[[str, dict[str, Any]], None]
CancelCallback = Callable[[], bool]


class PipelineCancelled(RuntimeError):
    """Raised when a caller requests cancellation at a pipeline boundary."""


def _emit_progress(progress: ProgressCallback | None, stage: str, **detail: Any) -> None:
    if progress:
        progress(stage, detail)


def _check_cancel(should_cancel: CancelCallback | None, stage: str) -> None:
    if should_cancel and should_cancel():
        raise PipelineCancelled(f"Pipeline cancelled during {stage}")


def _json_object_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(stripped[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


def _bounded_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _cap_includes(request: ResearchRequest, triage: list[TriageRecord]) -> None:
    include_limit = max(1, request.max_papers or 1)
    included = 0
    for row in triage:
        if row.decision != "include":
            continue
        included += 1
        if included <= include_limit:
            continue
        row.decision = "maybe"
        note = "Downgraded from include because it exceeded max_papers."
        row.llm_reason = f"{row.llm_reason} {note}".strip()
        row.reason = f"{row.reason} {note}".strip()


class ScholarPipeline:
    def __init__(self, config: ScholarForgeConfig | None = None):
        self.config = config or load_config()
        self.providers: dict[str, SearchProvider] = provider_registry()

    @classmethod
    def from_config(cls, config_path: str | Path | None = None) -> "ScholarPipeline":
        return cls(load_config(config_path))

    def apply_defaults(self, request: ResearchRequest) -> ResearchRequest:
        default_domain = self.config.default_domain()
        if not request.profile:
            request.profile = request.domain or default_domain
        if not request.domain:
            request.domain = default_domain
        if request.domain == "general" and request.profile != "general":
            request.domain = request.profile
        if not request.providers:
            request.providers = self.config.default_providers(request.profile)
        if request.max_papers is None or request.max_papers <= 0:
            request.max_papers = self.config.default_max_papers()
        if not request.year_range:
            request.year_range = self.config.default_year()
        if not request.language:
            request.language = self.config.default_language()
        return request

    def plan(self, request: ResearchRequest, out: str | Path | None = None) -> list[QueryRecord]:
        request = self.apply_defaults(request)
        queries = plan_queries(request, self.config)
        if out:
            writer = BundleWriter(out)
            writer.write_request(request)
            writer.write_queries(queries)
            writer.write_manifest(request, queries=len(queries))
        return queries

    def run(
        self,
        request: ResearchRequest | str | Path,
        *,
        out: str | Path,
        refresh: bool = False,
        progress: ProgressCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> Path:
        _check_cancel(should_cancel, "start")
        if isinstance(request, (str, Path)) and Path(request).exists():
            req = load_request(request)
        elif isinstance(request, ResearchRequest):
            req = request
        else:
            req = ResearchRequest(question=str(request))

        req = self.apply_defaults(req)
        writer = BundleWriter(out)
        _emit_progress(progress, "planning", question=req.question, out=str(writer.root))
        queries = self.plan(req, out=out)
        _emit_progress(progress, "planned", queries=len(queries), out=str(writer.root))
        _check_cancel(should_cancel, "planning")
        sources = self._search_all(
            req,
            queries,
            writer,
            refresh=refresh,
            progress=progress,
            should_cancel=should_cancel,
        )
        _check_cancel(should_cancel, "searching")
        _emit_progress(progress, "dedupe", sources=len(sources))
        deduped = dedupe_sources(sources)
        _check_cancel(should_cancel, "dedupe")
        _emit_progress(progress, "resources", sources=len(deduped))
        resources = extract_resources(req, deduped)
        _check_cancel(should_cancel, "resources")
        _emit_progress(progress, "ranking", sources=len(deduped))
        triage = rank_sources(req, deduped)
        if req.llm_triage:
            _check_cancel(should_cancel, "llm_triage")
            _emit_progress(progress, "llm_triage", sources=len(deduped))
            triage = self._apply_llm_triage(req, deduped, triage, writer)
        if req.read_pdf:
            _check_cancel(should_cancel, "read_pdf")
            _emit_progress(progress, "read_pdf", sources=len(deduped))
            self._read_selected_pdfs(req, deduped, triage, writer)
        _check_cancel(should_cancel, "evidence")
        _emit_progress(progress, "evidence", included=sum(1 for row in triage if row.decision == "include"))
        evidence = extract_evidence(req, deduped, triage)

        _check_cancel(should_cancel, "writing")
        _emit_progress(
            progress,
            "writing",
            sources=len(deduped),
            triage=len(triage),
            evidence=len(evidence),
            resources=len(resources),
        )
        writer.write_sources(deduped)
        writer.write_triage(triage)
        writer.write_evidence(evidence)
        writer.write_resources(resources)
        for source in deduped:
            if any(item.source_id == source.source_id for item in evidence):
                writer.write_note(source.source_id, note_for_source(source, evidence))
        fallback_brief = write_brief(req, deduped, triage, evidence, resources)
        writer.write_brief(fallback_brief)
        _check_cancel(should_cancel, "brief")
        _emit_progress(progress, "brief", llm_enabled=req.use_llm)
        brief = self._write_brief(req, deduped, triage, evidence, resources, writer, fallback=fallback_brief)
        if brief != fallback_brief:
            writer.write_brief(brief)
        writer.write_references(write_references(deduped, triage))
        writer.write_manifest(
            req,
            queries=len(queries),
            sources=len(deduped),
            triage=len(triage),
            evidence=len(evidence),
            resources=len(resources),
            extra={"completed_at": utc_now_iso()},
        )
        _emit_progress(
            progress,
            "done",
            out=str(writer.root),
            queries=len(queries),
            sources=len(deduped),
            evidence=len(evidence),
            resources=len(resources),
        )
        return writer.root

    def _write_brief(
        self,
        request: ResearchRequest,
        sources: list[SourceRecord],
        triage: list[Any],
        evidence: list[Any],
        resources: list[Any],
        writer: BundleWriter,
        fallback: str | None = None,
    ) -> str:
        fallback = fallback if fallback is not None else write_brief(request, sources, triage, evidence, resources)
        if not request.use_llm:
            return fallback
        try:
            from .llm import OpenAICompatibleLLM

            llm = OpenAICompatibleLLM(self.config)
            if not llm.available:
                return fallback
            prompt = build_llm_brief_prompt(request, sources, triage, evidence)
            brief = llm.complete_text(prompt, temperature=0.1, max_tokens=2200).strip()
            if not brief:
                return fallback
            writer.append_provenance(
                {
                    "timestamp": utc_now_iso(),
                    "provider": "llm_brief",
                    "status": "ok",
                    "model": self.config.llm_model,
                }
            )
            return append_resource_index(brief + "\n", request, resources)
        except Exception as exc:
            writer.append_provenance(
                {
                    "timestamp": utc_now_iso(),
                    "provider": "llm_brief",
                    "status": "error",
                    "error": str(exc),
                    "model": self.config.llm_model,
                }
            )
            return fallback

    def _apply_llm_triage(
        self,
        request: ResearchRequest,
        sources: list[SourceRecord],
        triage: list[TriageRecord],
        writer: BundleWriter,
    ) -> list[TriageRecord]:
        if not request.use_llm:
            writer.append_provenance(
                {
                    "timestamp": utc_now_iso(),
                    "provider": "llm_triage",
                    "status": "skipped",
                    "reason": "use_llm disabled",
                    "model": self.config.llm_model,
                }
            )
            return triage
        try:
            from .llm import OpenAICompatibleLLM

            llm = OpenAICompatibleLLM(self.config)
            if not llm.available:
                writer.append_provenance(
                    {
                        "timestamp": utc_now_iso(),
                        "provider": "llm_triage",
                        "status": "skipped",
                        "reason": "LLM API key is not configured",
                        "model": self.config.llm_model,
                    }
                )
                return triage
            prompt = self._build_llm_triage_prompt(request, sources, triage)
            response = llm.complete_text(prompt, temperature=0.0, max_tokens=1800)
            changed = self._merge_llm_triage_response(request, triage, response)
            writer.append_provenance(
                {
                    "timestamp": utc_now_iso(),
                    "provider": "llm_triage",
                    "status": "ok",
                    "model": self.config.llm_model,
                    "updated_count": changed,
                }
            )
            return triage
        except Exception as exc:
            writer.append_provenance(
                {
                    "timestamp": utc_now_iso(),
                    "provider": "llm_triage",
                    "status": "error",
                    "error": str(exc),
                    "model": self.config.llm_model,
                }
            )
            return triage

    def _build_llm_triage_prompt(
        self,
        request: ResearchRequest,
        sources: list[SourceRecord],
        triage: list[TriageRecord],
    ) -> str:
        by_source = {source.source_id: source for source in sources}
        rows = []
        for row in triage[: min(len(triage), 24)]:
            source = by_source.get(row.source_id)
            if not source:
                continue
            rows.append(
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "year": source.year,
                    "venue": source.venue,
                    "deterministic_score": row.total_score,
                    "deterministic_decision": row.decision,
                    "abstract_or_snippet": (source.abstract or source.snippet or source.raw.get("tldr", ""))[:900],
                }
            )
        return (
            "You are triaging scholarly sources for an audit-oriented research bundle.\n"
            "Use only the provided metadata. Return only JSON, no markdown.\n"
            "Decisions must be one of include, maybe, exclude. Include means directly useful evidence.\n"
            f"Question: {request.question}\n"
            f"Profile: {request.profile}\n"
            f"Max include count: {request.max_papers}\n"
            "Return this shape: "
            '{"triage":[{"source_id":"...","decision":"include|maybe|exclude","llm_score":0.0,"reason":"short reason"}]}\n'
            f"Sources:\n{json.dumps(rows, ensure_ascii=False, indent=2)}\n"
        )

    def _merge_llm_triage_response(
        self,
        request: ResearchRequest,
        triage: list[TriageRecord],
        response: str,
    ) -> int:
        data = _json_object_from_text(response)
        updates = data.get("triage")
        if not isinstance(updates, list):
            raise ValueError("LLM triage response must contain a triage list")
        by_id = {row.source_id: row for row in triage}
        changed = 0
        for item in updates:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id", ""))
            decision = item.get("decision")
            if source_id not in by_id or decision not in {"include", "maybe", "exclude"}:
                continue
            row = by_id[source_id]
            row.decision = decision
            score = item.get("llm_score")
            row.llm_score = _bounded_float(score) if score is not None else None
            row.llm_reason = str(item.get("reason", "") or "")
            row.reason = f"LLM triage override. {row.llm_reason}".strip()
            changed += 1
        _cap_includes(request, triage)
        return changed

    def _search_all(
        self,
        request: ResearchRequest,
        queries: list[QueryRecord],
        writer: BundleWriter,
        *,
        refresh: bool,
        progress: ProgressCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> list[SourceRecord]:
        all_sources: list[SourceRecord] = []
        limit = self.config.max_search_results_per_query()
        for query_index, query in enumerate(queries, start=1):
            _check_cancel(should_cancel, "searching")
            for provider_name in query.provider_targets:
                _check_cancel(should_cancel, "searching")
                _emit_progress(
                    progress,
                    "searching",
                    query=query.query,
                    query_index=query_index,
                    query_count=len(queries),
                    provider=provider_name,
                )
                provider = self.providers.get(provider_name)
                if provider is None:
                    writer.append_provenance(
                        {
                            "timestamp": utc_now_iso(),
                            "provider": provider_name,
                            "query": query.query,
                            "status": "skipped",
                            "error": "unknown provider",
                        }
                    )
                    continue
                if not self.config.provider_enabled(provider_name):
                    continue
                raw_key = f"{provider_name}|{query.query}|{request.year_range}|{limit}"
                raw_path = writer.raw_path(provider_name, raw_key)
                try:
                    if raw_path.exists() and not refresh:
                        raw = read_json(raw_path)
                        status = "cached"
                    else:
                        raw = provider.fetch(query, request, self.config, limit=limit)
                        writer.write_raw(provider_name, raw_key, raw)
                        status = "ok"
                    normalized = provider.normalize(raw, query, request)
                    all_sources.extend(normalized)
                    _emit_progress(
                        progress,
                        "search_result",
                        query=query.query,
                        provider=provider_name,
                        status=status,
                        result_count=len(normalized),
                    )
                    writer.append_provenance(
                        {
                            "timestamp": utc_now_iso(),
                            "provider": provider_name,
                            "query": query.query,
                            "status": status,
                            "raw_file": str(raw_path.relative_to(writer.root)),
                            "result_count": len(normalized),
                        }
                    )
                except PipelineCancelled:
                    raise
                except Exception as exc:
                    writer.append_provenance(
                        {
                            "timestamp": utc_now_iso(),
                            "provider": provider_name,
                            "query": query.query,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
        return all_sources

    def _read_selected_pdfs(
        self,
        request: ResearchRequest,
        sources: list[SourceRecord],
        triage: list[Any],
        writer: BundleWriter,
    ) -> None:
        included = {row.source_id for row in triage if row.decision == "include"}
        selected = [source for source in sources if source.source_id in included and source.pdf_url][:3]
        if not selected:
            return
        try:
            from .readers import download_pdf, extract_pdf_text
        except Exception as exc:
            writer.append_provenance(
                {
                    "timestamp": utc_now_iso(),
                    "provider": "pdf_reader",
                    "status": "error",
                    "error": str(exc),
                }
            )
            return
        pdf_root = writer.root / "raw" / "pdf"
        pdf_root.mkdir(parents=True, exist_ok=True)
        for source in selected:
            try:
                pdf_path = pdf_root / f"{source.source_id}.pdf"
                download_pdf(source.pdf_url, pdf_path)
                text = extract_pdf_text(pdf_path, max_pages=8)
                source.raw["pdf_text_preview"] = text[:4000]
                writer.append_provenance(
                    {
                        "timestamp": utc_now_iso(),
                        "provider": "pdf_reader",
                        "source_id": source.source_id,
                        "status": "ok",
                        "raw_file": str(pdf_path.relative_to(writer.root)),
                    }
                )
            except Exception as exc:
                writer.append_provenance(
                    {
                        "timestamp": utc_now_iso(),
                        "provider": "pdf_reader",
                        "source_id": source.source_id,
                        "status": "error",
                        "error": str(exc),
                    }
                )


def plan_research(
    request: ResearchRequest,
    *,
    out: str | Path | None = None,
    config_path: str | Path | None = None,
) -> list[QueryRecord]:
    return ScholarPipeline.from_config(config_path).plan(request, out=out)


def run_research(
    request: ResearchRequest,
    *,
    out: str | Path,
    refresh: bool = False,
    config_path: str | Path | None = None,
    progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> Path:
    return ScholarPipeline.from_config(config_path).run(
        request,
        out=out,
        refresh=refresh,
        progress=progress,
        should_cancel=should_cancel,
    )
