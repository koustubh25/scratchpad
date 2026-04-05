#!/usr/bin/env python3
"""CLI for the modernization demo tool."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from modernize_demo.core.invalidation import lock_is_stale
from modernize_demo.core.state import ProjectState


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="modernize", description="Modernization demo CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("source_path")
    init_parser.add_argument("--target-stack")
    init_parser.add_argument("--provider", default="demo-ai")
    init_parser.add_argument("--trust-level", default="standard")

    for simple in ["discover", "parse", "facts", "extract", "source-architect", "target-architect", "status"]:
        subparsers.add_parser(simple)

    choose_provider_parser = subparsers.add_parser("choose-provider")
    choose_provider_parser.add_argument("--provider")

    choose_stack_parser = subparsers.add_parser("choose-target-stack")
    choose_stack_parser.add_argument("--target-stack", required=True)
    choose_stack_parser.add_argument("--architecture-style", default="service-oriented")
    choose_stack_parser.add_argument("--deployment-style", default="single-deployable")

    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("app_name")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("app_name")

    review_parser = subparsers.add_parser("review")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)
    review_semantics_parser = review_subparsers.add_parser("semantics")
    review_semantics_parser.add_argument("module", nargs="?")
    review_subparsers.add_parser("source-architecture")
    review_subparsers.add_parser("target-architecture")

    correct_parser = subparsers.add_parser("correct")
    correct_subparsers = correct_parser.add_subparsers(dest="correct_command", required=True)
    correct_semantics_parser = correct_subparsers.add_parser("semantics")
    correct_semantics_parser.add_argument("module")
    correct_semantics_parser.add_argument("--field", required=True)
    correct_semantics_parser.add_argument("--value", required=True)

    approve_parser = subparsers.add_parser("approve")
    approve_subparsers = approve_parser.add_subparsers(dest="approve_command", required=True)
    approve_semantics_parser = approve_subparsers.add_parser("semantics")
    approve_semantics_parser.add_argument("module", nargs="?")
    approve_semantics_parser.add_argument("--all", dest="approve_all", action="store_true")
    approve_subparsers.add_parser("source-architecture")
    approve_subparsers.add_parser("target-architecture")

    lock_parser = subparsers.add_parser("lock")
    lock_subparsers = lock_parser.add_subparsers(dest="lock_command", required=True)
    lock_subparsers.add_parser("semantics")
    lock_subparsers.add_parser("source-architecture")
    lock_subparsers.add_parser("target-architecture")
    return parser


def parse_target_stack(value: str) -> list[dict[str, str]]:
    """Parse target-stack CLI input."""
    entries = []
    for chunk in value.split(","):
        adapter, role = chunk.split(":", 1)
        entries.append({"adapter": adapter.strip(), "role": role.strip()})
    return entries


def emit(payload: Any) -> None:
    """Print JSON output for easy testing and inspection."""
    print(json.dumps(payload, indent=2, sort_keys=True))


def warn(message: str) -> None:
    """Print a human-readable warning to stderr without affecting JSON output."""
    print(f"WARNING: {message}", file=sys.stderr)


def choose_provider_interactively() -> str:
    """Prompt the user to choose a provider interactively."""
    print("Select AI provider:")
    print("1. demo-ai (default offline fallback)")
    print("2. openai")
    print("3. anthropic")
    print("4. gemini")
    print("5. command-json (run any local JSON stdin/stdout command)")
    print("6. python:<module>:<symbol> (load a Python provider)")
    print("7. Custom provider string")
    choice = input("Enter choice [1]: ").strip() or "1"

    if choice == "1":
        return "demo-ai"
    if choice == "2":
        return "openai"
    if choice == "3":
        return "anthropic"
    if choice == "4":
        return "gemini"
    if choice == "5":
        return "command-json"
    if choice == "6":
        module = input("Python module: ").strip()
        symbol = input("Provider class or factory symbol: ").strip()
        if not module or not symbol:
            raise RuntimeError("python provider requires both module and symbol")
        return f"python:{module}:{symbol}"
    if choice == "7":
        provider = input("Provider string: ").strip()
        if not provider:
            raise RuntimeError("custom provider string cannot be empty")
        return provider
    raise RuntimeError("invalid provider selection")


def run_cli(argv: list[str] | None = None, project_root: str | Path = ".") -> int:
    """Execute the CLI and return an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    resolved_root = Path(os.environ.get("MODERNIZE_PROJECT_ROOT", project_root))
    state = ProjectState(resolved_root)

    if args.command == "init":
        target_stack = parse_target_stack(args.target_stack) if args.target_stack else []
        state.init(args.source_path, target_stack, args.provider, args.trust_level)
        emit(
            {
                "status": "initialized",
                "stateDir": str(state.modernize_dir),
                "provider": args.provider,
            }
        )
        return 0

    if not state.is_initialized:
        parser.error("project not initialized; run init first")

    if args.command == "choose-provider":
        provider = args.provider
        if not provider:
            if not sys.stdin.isatty():
                parser.error("choose-provider without --provider requires an interactive terminal")
            provider = choose_provider_interactively()
        project = state.update_project_config(provider=provider)
        emit({"status": "provider-updated", "provider": project["provider"]})
        return 0
    if args.command == "discover":
        from modernize_demo.pipeline.discover import run_discover

        emit(run_discover(state))
        return 0
    if args.command == "choose-target-stack":
        from modernize_demo.pipeline.target_architect import choose_target_stack

        emit(
            choose_target_stack(
                state,
                parse_target_stack(args.target_stack),
                architecture_style=args.architecture_style,
                deployment_style=args.deployment_style,
            )
        )
        return 0
    if args.command == "parse":
        from modernize_demo.pipeline.parser import run_parse

        emit({"modules": run_parse(state)})
        return 0
    if args.command == "facts":
        from modernize_demo.pipeline.facts import run_facts

        emit({"facts": run_facts(state)})
        return 0
    if args.command == "extract":
        from modernize_demo.pipeline.extractor import run_extract

        provider = state.load_migration()["project"]["provider"]
        if provider == "demo-ai":
            warn(
                "semantic extraction is using the offline demo-ai fallback. "
                "Run 'python3 modernize.py choose-provider' before extract to use another AI provider."
            )
        emit({"semantics": run_extract(state)})
        return 0
    if args.command == "source-architect":
        from modernize_demo.pipeline.source_architect import run_source_architect

        emit(run_source_architect(state))
        return 0
    if args.command == "target-architect":
        from modernize_demo.pipeline.target_architect import run_target_architect

        emit(run_target_architect(state))
        return 0
    if args.command == "generate":
        from modernize_demo.pipeline.generator import run_generate

        emit(run_generate(state, args.app_name))
        return 0
    if args.command == "verify":
        from modernize_demo.pipeline.verifier import run_verify

        emit(run_verify(state, args.app_name))
        return 0
    if args.command == "review" and args.review_command == "semantics":
        from modernize_demo.pipeline.reviewer import review_semantics

        emit(review_semantics(state, args.module))
        return 0
    if args.command == "review" and args.review_command == "source-architecture":
        from modernize_demo.pipeline.source_architect import review_source_architecture

        emit(review_source_architecture(state))
        return 0
    if args.command == "review" and args.review_command == "target-architecture":
        from modernize_demo.pipeline.target_architect import review_target_architecture

        emit(review_target_architecture(state))
        return 0
    if args.command == "correct" and args.correct_command == "semantics":
        from modernize_demo.pipeline.reviewer import correct_semantics

        emit(correct_semantics(state, args.module, args.field, args.value))
        return 0
    if args.command == "approve" and args.approve_command == "semantics":
        from modernize_demo.pipeline.reviewer import approve_semantics

        module = None if args.approve_all else args.module
        emit(approve_semantics(state, module=module))
        return 0
    if args.command == "approve" and args.approve_command == "source-architecture":
        from modernize_demo.pipeline.source_architect import approve_source_architecture

        emit(approve_source_architecture(state))
        return 0
    if args.command == "approve" and args.approve_command == "target-architecture":
        from modernize_demo.pipeline.target_architect import approve_target_architecture

        emit(approve_target_architecture(state))
        return 0
    if args.command == "lock" and args.lock_command == "semantics":
        from modernize_demo.pipeline.locker import lock_semantics

        emit(lock_semantics(state))
        return 0
    if args.command == "lock" and args.lock_command == "source-architecture":
        from modernize_demo.pipeline.source_architect import lock_source_architecture

        emit(lock_source_architecture(state))
        return 0
    if args.command == "lock" and args.lock_command == "target-architecture":
        from modernize_demo.pipeline.target_architect import lock_target_architecture

        emit(lock_target_architecture(state))
        return 0
    if args.command == "status":
        emit(_status_payload(state))
        return 0

    parser.error("unsupported command")
    return 2


def _status_payload(state: ProjectState) -> dict[str, Any]:
    """Render a compact status payload."""
    migration = state.load_migration()
    semantic_stale, semantic_reason = lock_is_stale(state, "semantic-lock.json")
    return {
        "project": migration["project"],
        "pipeline": migration["pipeline"],
        "locks": {
            "semantic": {
                "exists": state.path_for("locked", "semantic-lock.json").exists(),
                "stale": semantic_stale,
                "reason": semantic_reason,
            },
            "sourceArchitecture": {
                "exists": state.path_for("locked", "source-architecture-lock.json").exists(),
            },
            "targetArchitecture": {
                "exists": state.path_for("locked", "target-architecture-lock.json").exists(),
            },
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_cli())
