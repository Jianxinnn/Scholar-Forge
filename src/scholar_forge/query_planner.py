from __future__ import annotations

from .config import ScholarForgeConfig
from .models import QueryRecord, ResearchRequest


def plan_queries(request: ResearchRequest, config: ScholarForgeConfig) -> list[QueryRecord]:
    providers = request.providers or config.default_providers(request.profile)
    explicit_providers = bool(request.providers)
    profile = config.profile(request.profile)
    expansions = list(profile.get("query_expansions") or [])
    focus = list(profile.get("evidence_focus") or [])

    candidates: list[QueryRecord] = [
        QueryRecord(
            query=request.question,
            intent="discovery",
            provider_targets=providers,
            rationale="Original research question.",
        )
    ]

    if request.year_range:
        candidates.append(
            QueryRecord(
                query=f"{request.question} {request.year_range}",
                intent="recent_scope",
                provider_targets=providers,
                rationale="Question with requested year scope.",
            )
        )

    if expansions:
        candidates.append(
            QueryRecord(
                query=f"{request.question} {' OR '.join(expansions[:3])}",
                intent="expanded_terms",
                provider_targets=providers,
                rationale=f"Profile expansion for {request.profile}.",
            )
        )

    if request.profile == "biomol":
        validation_targets = providers if explicit_providers else ["semantic_scholar", "pubmed", "openalex"]
        limitation_targets = providers if explicit_providers else ["semantic_scholar", "pubmed", "tavily"]
        candidates.extend(
            [
                QueryRecord(
                    query=f"{request.question} benchmark dataset validation",
                    intent="biomol_validation",
                    provider_targets=validation_targets,
                    rationale="Prioritize benchmark, dataset, and validation evidence.",
                ),
                QueryRecord(
                    query=f"{request.question} limitations reproducibility safety",
                    intent="biomol_limitations",
                    provider_targets=limitation_targets,
                    rationale="Find limitations, reproducibility, and caveats.",
                ),
            ]
        )
    elif request.profile == "agent_skills":
        targets = providers if explicit_providers else ["tavily", "semantic_scholar", "openalex", "arxiv"]
        candidates.extend(
            [
                QueryRecord(
                    query="LLM agent skill library self-improvement skill acquisition tool use",
                    intent="agent_skill_core",
                    provider_targets=targets,
                    rationale="Focus on skill libraries and self-improving LLM agents.",
                ),
                QueryRecord(
                    query="self-evolving agents lifelong learning memory reflection tool-grounded learning",
                    intent="self_evolving_agents",
                    provider_targets=targets,
                    rationale="Find self-evolution loops, memory, reflection, and tool-grounded learning.",
                ),
                QueryRecord(
                    query="SKILL.md agent skills Model Context Protocol security acquisition survey",
                    intent="agent_skill_layer",
                    provider_targets=targets,
                    rationale="Find the emerging skill abstraction layer and governance work.",
                ),
            ]
        )
    elif focus:
        candidates.append(
            QueryRecord(
                query=f"{request.question} {' '.join(focus[:3])}",
                intent="evidence_focus",
                provider_targets=providers,
                rationale="Search for evidence-bearing claims and limitations.",
            )
        )

    seen: set[str] = set()
    unique: list[QueryRecord] = []
    for record in candidates:
        key = record.query.strip().lower()
        if key and key not in seen:
            seen.add(key)
            record.provider_targets = [p for p in record.provider_targets if config.provider_enabled(p)]
            unique.append(record)
    return unique
