# AGENTS.md

Follow the repository-level guidelines from `/Users/jxtang/Desktop/CodeProjects`.

Project-specific constraints:

- Keep the core library lightweight and framework-free.
- Do not introduce LangChain, Agno, LiteLLM, vector databases, or daemon state for MVP work.
- Keep provider integrations behind small provider classes.
- Default tests must be offline and deterministic.
- Bundle files are part of the product contract; avoid casual schema churn.

