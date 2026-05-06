from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bundle import inspect_bundle
from .config import load_config, write_config_template
from .models import QueryRecord, ResearchRequest
from .pipeline import ScholarPipeline
from .providers import provider_registry


def _providers(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _request_from_args(args: argparse.Namespace) -> ResearchRequest:
    return ResearchRequest(
        question=args.question,
        domain=args.domain or "",
        profile=args.profile or "",
        year_range=args.year or "",
        max_papers=args.max_papers,
        providers=_providers(args.providers),
        language=args.language or "",
        read_pdf=bool(getattr(args, "read_pdf", False)),
        use_llm=not bool(getattr(args, "no_llm", False)),
        llm_triage=bool(getattr(args, "llm_triage", False)),
    )


def cmd_init(args: argparse.Namespace) -> int:
    path = write_config_template(args.path, force=args.force)
    print(f"Wrote config template: {path}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    pipeline = ScholarPipeline.from_config(args.config)
    request = _request_from_args(args)
    queries = pipeline.plan(request, out=args.out)
    print(f"Planned {len(queries)} queries")
    print(f"Bundle: {Path(args.out).resolve()}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    pipeline = ScholarPipeline.from_config(args.config)
    request = _request_from_args(args)
    root = pipeline.run(request, out=args.out, refresh=args.refresh)
    print(f"Wrote scholar bundle: {root.resolve()}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    info = inspect_bundle(args.bundle)
    print(f"Bundle: {info['root']}")
    print(f"Question: {info['question']}")
    print(f"Profile: {info['profile']}")
    counts = info["counts"]
    print(
        "Counts: "
        f"queries={counts['queries']} sources={counts['sources']} "
        f"include={counts['include']} maybe={counts['maybe']} "
        f"exclude={counts['exclude']} evidence={counts['evidence']}"
    )
    missing = [name for name, exists in info["files"].items() if not exists]
    if missing:
        print(f"Missing files: {', '.join(missing)}")
        return 1
    print("Files: ok")
    if info["validation_errors"]:
        print("Schema: error")
        for error in info["validation_errors"]:
            print(f"  - {error}")
        return 1
    print("Schema: ok")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print("ScholarForge doctor")
    print(f"Config: {config.path or 'built-in/env only'}")
    print(f"LLM model: {config.llm_model}")
    print(f"LLM base URL: {config.llm_base_url or 'default OpenAI-compatible URL'}")
    print(f"LLM API key: {'configured' if config.llm_api_key else 'missing'}")
    print("")
    providers = provider_registry()
    failures = 0
    for name, provider in providers.items():
        status = provider.status(config)
        state = "ok" if status.available else "missing"
        enabled = "enabled" if status.enabled else "disabled"
        print(f"{name}: {enabled}, {state} - {status.detail}")
        if status.enabled and not status.available:
            failures += 1
        if args.network and status.enabled and status.available:
            try:
                raw = provider.fetch(
                    QueryRecord(query=args.query, provider_targets=[name]),
                    ResearchRequest(question=args.query, providers=[name]),
                    config,
                    limit=1,
                )
                normalized = provider.normalize(
                    raw,
                    QueryRecord(query=args.query, provider_targets=[name]),
                    ResearchRequest(question=args.query, providers=[name]),
                )
                print(f"  network: ok ({len(normalized)} result(s))")
            except Exception as exc:
                failures += 1
                print(f"  network: error - {exc}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scholar-forge", description="Build structured scholarly research bundles.")
    parser.add_argument("--config", default=None, help="Path to scholarforge.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Write a scholarforge.yaml template")
    init.add_argument("--path", default="scholarforge.yaml")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    def add_research_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("question")
        p.add_argument("--out", default="./scholar-bundle")
        p.add_argument("--profile", default=None)
        p.add_argument("--domain", default=None)
        p.add_argument("--year", default=None)
        p.add_argument("--max-papers", type=int, default=None)
        p.add_argument("--providers", default=None, help="Comma-separated provider names")
        p.add_argument("--language", default=None)
        p.add_argument("--no-llm", action="store_true")

    plan = sub.add_parser("plan", help="Plan queries and write request/queries")
    add_research_args(plan)
    plan.set_defaults(func=cmd_plan)

    run = sub.add_parser("run", help="Run the full research bundle pipeline")
    add_research_args(run)
    run.add_argument("--read-pdf", action="store_true")
    run.add_argument("--llm-triage", action="store_true")
    run.add_argument("--refresh", action="store_true")
    run.set_defaults(func=cmd_run)

    inspect = sub.add_parser("inspect", help="Inspect a scholar-bundle directory")
    inspect.add_argument("bundle")
    inspect.set_defaults(func=cmd_inspect)

    doctor = sub.add_parser("doctor", help="Check configuration and provider availability")
    doctor.add_argument("--network", action="store_true", help="Run live one-result provider checks")
    doctor.add_argument("--query", default="protein design")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
