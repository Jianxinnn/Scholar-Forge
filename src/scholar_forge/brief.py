from __future__ import annotations

from collections import Counter

from .models import EvidenceRecord, ResearchRequest, ResourceRecord, SourceRecord, TriageRecord


def _wants_chinese(language: str) -> bool:
    normalized = language.strip().lower()
    return normalized.startswith("zh") or normalized in {"cn", "chinese", "中文"}


def write_brief(
    request: ResearchRequest,
    sources: list[SourceRecord],
    triage: list[TriageRecord],
    evidence: list[EvidenceRecord],
    resources: list[ResourceRecord] | None = None,
) -> str:
    if _wants_chinese(request.language):
        return _write_brief_zh(request, sources, triage, evidence, resources or [])

    by_source = {source.source_id: source for source in sources}
    triage_by_source = {row.source_id: row for row in triage}
    included = [row for row in triage if row.decision == "include"]
    included.sort(key=lambda row: row.total_score, reverse=True)
    max_papers = request.max_papers or 30

    lines: list[str] = [
        "# Research Brief",
        "",
        "## Question",
        request.question,
        "",
        "## Search Scope",
        f"- Profile: {request.profile}",
        f"- Domain: {request.domain}",
        f"- Year range: {request.year_range or 'not specified'}",
        f"- Max papers: {max_papers}",
        f"- Providers: {', '.join(request.providers) if request.providers else 'profile defaults'}",
        "",
        "## Main Findings",
    ]

    if not evidence:
        lines.append("- No evidence records were generated. Check provider availability and query scope.")
    else:
        for item in evidence[:10]:
            source = by_source.get(item.source_id)
            title = source.title if source else item.source_id
            lines.append(f"- {item.evidence_text[:240]} [{item.source_id}; {title}]")

    lines.extend(["", "## Evidence Matrix", "", "| Claim | Source | Direction | Confidence |", "| --- | --- | --- | --- |"])
    for item in evidence[:20]:
        lines.append(
            f"| {item.claim[:80]} | {item.source_id} | {item.supports_or_contradicts} | {item.confidence:.2f} |"
        )

    lines.extend(["", "## Key Papers", ""])
    for row in included[:max_papers]:
        source = by_source.get(row.source_id)
        if not source:
            continue
        year = f" ({source.year})" if source.year else ""
        venue = f" - {source.venue}" if source.venue else ""
        score = triage_by_source[source.source_id].total_score
        lines.append(f"- [{source.source_id}] {source.title}{year}{venue}; score={score:.3f}")

    lines.extend(["", "## Gaps / Open Questions", ""])
    if len(included) < max_papers:
        lines.append("- Fewer sources were included than requested; broaden queries or enable more providers.")
    lines.append("- Confirm important claims against full text before using them in a manuscript or execution plan.")
    if not request.read_pdf:
        lines.append("- PDF reading was not enabled; current evidence is based on metadata, abstracts, snippets, or TLDRs.")

    lines.extend(["", "## Next Actions", ""])
    lines.append("- Review `triage.jsonl` for excluded or borderline sources.")
    lines.append("- Deep-read top included papers before turning claims into experimental constraints.")
    lines.append("- Record durable claims and contradictions in Cairn only after evidence is checked.")
    return append_resource_index("\n".join(lines).strip() + "\n", request, resources or [])


def _write_brief_zh(
    request: ResearchRequest,
    sources: list[SourceRecord],
    triage: list[TriageRecord],
    evidence: list[EvidenceRecord],
    resources: list[ResourceRecord],
) -> str:
    by_source = {source.source_id: source for source in sources}
    triage_by_source = {row.source_id: row for row in triage}
    included = [row for row in triage if row.decision == "include"]
    included.sort(key=lambda row: row.total_score, reverse=True)
    max_papers = request.max_papers or 30

    lines: list[str] = [
        "# 研究简报",
        "",
        "## 问题",
        request.question,
        "",
        "## 检索范围",
        f"- Profile: {request.profile}",
        f"- Domain: {request.domain}",
        f"- Year range: {request.year_range or '未指定'}",
        f"- Max papers: {max_papers}",
        f"- Providers: {', '.join(request.providers) if request.providers else 'profile defaults'}",
        "",
        "## 主要发现",
    ]

    if not evidence:
        lines.append("- 未生成 evidence 记录；请检查 provider 可用性和查询范围。")
    else:
        for item in evidence[:10]:
            source = by_source.get(item.source_id)
            title = source.title if source else item.source_id
            lines.append(f"- {item.evidence_text[:240]} [{item.source_id}; {title}]")

    lines.extend(["", "## 证据矩阵", "", "| Claim | Source | Direction | Confidence |", "| --- | --- | --- | --- |"])
    for item in evidence[:20]:
        lines.append(
            f"| {item.claim[:80]} | {item.source_id} | {item.supports_or_contradicts} | {item.confidence:.2f} |"
        )

    lines.extend(["", "## 关键文献", ""])
    for row in included[:max_papers]:
        source = by_source.get(row.source_id)
        if not source:
            continue
        year = f" ({source.year})" if source.year else ""
        venue = f" - {source.venue}" if source.venue else ""
        score = triage_by_source[source.source_id].total_score
        lines.append(f"- [{source.source_id}] {source.title}{year}{venue}; score={score:.3f}")

    lines.extend(["", "## 缺口 / 待确认问题", ""])
    if len(included) < max_papers:
        lines.append("- included 来源少于请求数量；可放宽查询或启用更多 provider。")
    lines.append("- 将重要结论用于论文或执行计划前，应核对全文。")
    if not request.read_pdf:
        lines.append("- PDF reading 未启用；当前 evidence 基于元数据、摘要、snippet 或 TLDR。")

    lines.extend(["", "## 下一步", ""])
    lines.append("- 复核 `triage.jsonl` 中被排除或边界状态的来源。")
    lines.append("- 将 claims 转成实验约束前，先深读 top included papers。")
    lines.append("- 只有在证据含义清楚后，才把 durable claims 和 contradictions 记录到 Cairn。")
    return append_resource_index("\n".join(lines).strip() + "\n", request, resources)


def _resource_url(resource: ResourceRecord) -> str:
    if resource.url:
        return resource.url
    for item in resource.access:
        url = item.get("url", "")
        if url:
            return url
    return ""


def _resource_index_lines(request: ResearchRequest, resources: list[ResourceRecord]) -> list[str]:
    chinese = _wants_chinese(request.language)
    heading = "## 资源索引" if chinese else "## Resource Index"
    lines = ["", heading, ""]
    if not resources:
        lines.append("- No candidate resources were identified." if not chinese else "- 未识别到候选 resource。")
        return lines

    counts = Counter(resource.resource_kind for resource in resources)
    for kind, count in sorted(counts.items()):
        suffix = "" if count == 1 else "s"
        if chinese:
            lines.append(f"- {kind}: {count} candidate resources")
        else:
            lines.append(f"- {kind}: {count} candidate resource{suffix}")

    lines.extend(["", "Representative resources:"])
    for resource in sorted(resources, key=lambda item: (-item.confidence, item.resource_kind, item.title.lower()))[:5]:
        url = _resource_url(resource)
        label = resource.title or resource.resource_id
        if url:
            lines.append(f"- {resource.resource_kind}: {label} - {url}")
        else:
            lines.append(f"- {resource.resource_kind}: {label}")
    return lines


def append_resource_index(brief: str, request: ResearchRequest, resources: list[ResourceRecord]) -> str:
    if "## Resource Index" in brief or "## 资源索引" in brief:
        return brief if brief.endswith("\n") else brief + "\n"
    return brief.rstrip() + "\n" + "\n".join(_resource_index_lines(request, resources)).rstrip() + "\n"


def build_llm_brief_prompt(
    request: ResearchRequest,
    sources: list[SourceRecord],
    triage: list[TriageRecord],
    evidence: list[EvidenceRecord],
) -> str:
    by_source = {source.source_id: source for source in sources}
    included = [row for row in triage if row.decision == "include"]
    included.sort(key=lambda row: row.total_score, reverse=True)

    source_blocks: list[str] = []
    for row in included[:16]:
        source = by_source.get(row.source_id)
        if not source:
            continue
        text = source.abstract or source.snippet or source.raw.get("tldr", "") or ""
        source_blocks.append(
            "\n".join(
                [
                    f"ID: {source.source_id}",
                    f"Title: {source.title}",
                    f"Year: {source.year or 'unknown'}",
                    f"Venue: {source.venue or 'unknown'}",
                    f"URL: {source.url or source.pdf_url}",
                    f"Score: {row.total_score:.3f}",
                    f"Evidence: {text[:700]}",
                ]
            )
        )

    if _wants_chinese(request.language):
        language_instruction = "Write in Chinese unless the source title must stay in English."
        required_structure = "\n".join(
            [
                "# Research Brief",
                "## 一句话结论",
                "## 主要研究路线",
                "## 前沿代表工作",
                "## 设计启示",
                "## 风险与缺口",
                "## 建议下一步",
                "## Key Sources",
            ]
        )
    else:
        language_instruction = "Write in English."
        required_structure = "\n".join(
            [
                "# Research Brief",
                "## One-Sentence Conclusion",
                "## Main Research Directions",
                "## Representative Recent Work",
                "## Design Implications",
                "## Risks and Gaps",
                "## Recommended Next Steps",
                "## Key Sources",
            ]
        )

    return f"""You are writing an audit-oriented research brief for an agent system.

Question:
{request.question}

Scope:
- profile: {request.profile}
- year range: {request.year_range or "not specified"}
- providers: {", ".join(request.providers)}

Use only the provided sources. Keep the brief concise, technical, and citation-grounded.
Every substantive claim must cite source IDs like [src_x, src_y].
Do not invent bibliographic details.

{language_instruction}

Required structure:
{required_structure}

Sources:
{chr(10).join("---" + chr(10) + block for block in source_blocks)}
"""
