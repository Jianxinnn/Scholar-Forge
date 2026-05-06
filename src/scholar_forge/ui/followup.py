from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from scholar_forge.config import ScholarForgeConfig


def _source_label(source: dict[str, Any]) -> str:
    year = f" ({source.get('year')})" if source.get("year") else ""
    venue = f", {source.get('venue')}" if source.get("venue") else ""
    return f"{source.get('title', source.get('source_id', 'source'))}{year}{venue}"


def _resolve_source_id(bundle: dict[str, Any], source_id: str = "", question: str = "") -> str:
    if source_id:
        return source_id
    text = question.lower()
    for source in bundle.get("sources", []):
        candidate = str(source.get("source_id", ""))
        if candidate and candidate.lower() in text:
            return candidate
    return ""


def _top_sources(bundle: dict[str, Any]) -> str:
    included = [
        source
        for source in bundle.get("sources", [])
        if (source.get("triage") or {}).get("decision") == "include"
    ]
    if not included:
        return "No included sources are available in this bundle yet."
    lines = ["Top included sources:"]
    for source in included[:8]:
        triage = source.get("triage") or {}
        score = float(triage.get("total_score", 0.0) or 0.0)
        lines.append(f"- [{source['source_id']}] {_source_label(source)}; score={score:.3f}")
    return "\n".join(lines)


def _why_decision(bundle: dict[str, Any], source_id: str) -> str:
    if not source_id:
        return "Pick a source first, or include its source_id in the question."
    for source in bundle.get("sources", []):
        if source.get("source_id") != source_id:
            continue
        triage = source.get("triage") or {}
        decision = triage.get("decision", "unknown")
        score = float(triage.get("total_score", 0.0) or 0.0)
        reason = triage.get("reason") or "No triage reason was recorded."
        llm_reason = triage.get("llm_reason") or ""
        suffix = f"\nLLM reason: {llm_reason}" if llm_reason else ""
        return f"[{source_id}] is `{decision}` with score={score:.3f}.\nReason: {reason}{suffix}"
    return f"Source not found in this bundle: {source_id}"


def _evidence_for(bundle: dict[str, Any], source_id: str) -> str:
    if not source_id:
        return "Pick a source first, or include its source_id in the question."
    rows = [item for item in bundle.get("evidence", []) if item.get("source_id") == source_id]
    if not rows:
        return f"No evidence records were generated for [{source_id}]."
    lines = [f"Evidence for [{source_id}]:"]
    for item in rows[:8]:
        text = str(item.get("evidence_text", "")).replace("\n", " ")[:360]
        lines.append(f"- [{item.get('evidence_id')}] {text}")
    return "\n".join(lines)


def _resources_by_kind(bundle: dict[str, Any]) -> str:
    resources = bundle.get("resources", [])
    if not resources:
        return "No candidate resources were identified in this bundle."
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for resource in resources:
        grouped[str(resource.get("resource_kind", "other"))].append(resource)
    lines = ["Resources by kind:"]
    for kind, rows in sorted(grouped.items()):
        lines.append(f"- {kind}: {len(rows)}")
        for resource in rows[:3]:
            label = resource.get("title") or resource.get("resource_id")
            url = f" - {resource.get('url')}" if resource.get("url") else ""
            lines.append(f"  - {label}{url}")
    return "\n".join(lines)


def _gaps(bundle: dict[str, Any]) -> str:
    counts = Counter((row.get("triage") or {}).get("decision", "unknown") for row in bundle.get("sources", []))
    evidence_count = len(bundle.get("evidence", []))
    request = bundle.get("request") or {}
    lines = [
        "Bundle gaps to review:",
        f"- Included sources: {counts.get('include', 0)}; maybe: {counts.get('maybe', 0)}; excluded: {counts.get('exclude', 0)}.",
        f"- Evidence records: {evidence_count}.",
    ]
    if counts.get("include", 0) < int(request.get("max_papers") or 0):
        lines.append("- Fewer sources were included than requested; consider broadening the query or enabling more providers.")
    if not request.get("read_pdf"):
        lines.append("- PDF reading was not enabled; evidence may be limited to abstracts, snippets, and metadata.")
    if not evidence_count:
        lines.append("- No evidence records exist yet; check provider availability and query scope.")
    return "\n".join(lines)


def _provider_errors(bundle: dict[str, Any]) -> str:
    rows = [row for row in bundle.get("provenance", []) if row.get("status") == "error"]
    if not rows:
        return "No provider or pipeline errors were recorded in provenance."
    lines = ["Recorded errors:"]
    for row in rows[:12]:
        provider = row.get("provider", "unknown")
        query = f" query={row.get('query')!r}" if row.get("query") else ""
        lines.append(f"- {provider}:{query} {row.get('error', '')}")
    return "\n".join(lines)


def infer_intent(question: str) -> str:
    text = question.lower()
    if any(term in text for term in ["provider", "provenance", "error", "failed"]):
        return "provider_errors"
    if any(term in text for term in ["resource", "dataset", "code", "pdf", "structure"]):
        return "resources_by_kind"
    if any(term in text for term in ["gap", "missing", "weak", "limitation"]):
        return "gaps"
    if any(term in text for term in ["why", "decision", "include", "exclude", "maybe"]):
        return "why_decision"
    if "evidence" in text:
        return "evidence_for"
    if any(term in text for term in ["top", "key", "important", "best", "paper"]):
        return "top_sources"
    return ""


def answer_deterministic(
    bundle: dict[str, Any],
    *,
    intent: str = "",
    question: str = "",
    source_id: str = "",
) -> dict[str, Any] | None:
    resolved_intent = intent or infer_intent(question)
    resolved_source_id = _resolve_source_id(bundle, source_id, question)
    if resolved_intent == "top_sources":
        return {"mode": "deterministic", "intent": resolved_intent, "answer": _top_sources(bundle)}
    if resolved_intent == "why_decision":
        return {"mode": "deterministic", "intent": resolved_intent, "answer": _why_decision(bundle, resolved_source_id)}
    if resolved_intent == "evidence_for":
        return {"mode": "deterministic", "intent": resolved_intent, "answer": _evidence_for(bundle, resolved_source_id)}
    if resolved_intent == "resources_by_kind":
        return {"mode": "deterministic", "intent": resolved_intent, "answer": _resources_by_kind(bundle)}
    if resolved_intent == "gaps":
        return {"mode": "deterministic", "intent": resolved_intent, "answer": _gaps(bundle)}
    if resolved_intent == "provider_errors":
        return {"mode": "deterministic", "intent": resolved_intent, "answer": _provider_errors(bundle)}
    return None


def build_llm_context(bundle: dict[str, Any]) -> str:
    source_rows = []
    for source in bundle.get("sources", [])[:20]:
        triage = source.get("triage") or {}
        source_rows.append(
            {
                "source_id": source.get("source_id"),
                "title": source.get("title"),
                "year": source.get("year"),
                "venue": source.get("venue"),
                "decision": triage.get("decision"),
                "score": triage.get("total_score"),
                "url": source.get("url") or source.get("pdf_url"),
                "abstract_or_snippet": (source.get("abstract") or source.get("snippet") or "")[:700],
            }
        )
    evidence_rows = [
        {
            "evidence_id": item.get("evidence_id"),
            "source_id": item.get("source_id"),
            "claim": item.get("claim"),
            "evidence_text": str(item.get("evidence_text", ""))[:700],
        }
        for item in bundle.get("evidence", [])[:30]
    ]
    resource_rows = [
        {
            "resource_id": item.get("resource_id"),
            "resource_kind": item.get("resource_kind"),
            "source_ids": item.get("source_ids"),
            "title": item.get("title"),
            "url": item.get("url"),
        }
        for item in bundle.get("resources", [])[:20]
    ]
    errors = [
        {
            "provider": row.get("provider"),
            "query": row.get("query"),
            "error": row.get("error"),
        }
        for row in bundle.get("provenance", [])
        if row.get("status") == "error"
    ][:12]
    return json.dumps(
        {
            "request": bundle.get("request", {}),
            "sources": source_rows,
            "evidence": evidence_rows,
            "resources": resource_rows,
            "errors": errors,
        },
        ensure_ascii=False,
        indent=2,
    )


def answer_with_llm(question: str, bundle: dict[str, Any], config: ScholarForgeConfig) -> dict[str, Any]:
    from scholar_forge.llm import OpenAICompatibleLLM

    llm = OpenAICompatibleLLM(config)
    if not llm.available:
        return {
            "mode": "unavailable",
            "intent": "",
            "answer": "LLM follow-up is not configured. Use a quick question or configure SCHOLARFORGE_LLM_API_KEY.",
        }
    prompt = (
        "You are answering a follow-up about one ScholarForge evidence bundle.\n"
        "Use only the bundle context below. If the context is insufficient, say so.\n"
        "Cite source_id or evidence_id in square brackets for every substantive claim.\n"
        "Keep the answer concise.\n\n"
        f"Question:\n{question}\n\n"
        f"Bundle context:\n{build_llm_context(bundle)}\n"
    )
    answer = llm.complete_text(prompt, temperature=0.0, max_tokens=900).strip()
    return {"mode": "llm", "intent": "", "answer": answer}


def answer_followup(
    bundle: dict[str, Any],
    *,
    question: str = "",
    intent: str = "",
    source_id: str = "",
    config: ScholarForgeConfig | None = None,
) -> dict[str, Any]:
    deterministic = answer_deterministic(bundle, intent=intent, question=question, source_id=source_id)
    if deterministic:
        return deterministic
    if config is not None and question.strip():
        return answer_with_llm(question, bundle, config)
    return {
        "mode": "deterministic",
        "intent": "",
        "answer": (
            "Ask a bundle-grounded question, or use one of the quick actions: top sources, "
            "resources, gaps, provider errors, why a source was triaged, or evidence for a source."
        ),
    }
