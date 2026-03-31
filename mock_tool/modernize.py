#!/usr/bin/env python3
"""modernize CLI — AI-Powered Legacy App Modernization (Mock Demo)."""

import sys
import os

# Add mock_tool to path so imports work when running from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.state import ProjectState

console = Console()


def get_state() -> ProjectState:
    return ProjectState(".")


@click.group()
def cli():
    """modernize — AI-Powered Legacy App Modernization Framework (v2)"""
    pass


# ── init ──────────────────────────────────────────────────────────────

@cli.command()
@click.argument("source_path")
@click.option("--target-stack", required=True, help="Target stack (e.g. react:frontend,go:backend)")
@click.option("--provider", default="claude", help="AI provider (claude, openai, gemini)")
@click.option("--trust-level", default="standard", help="Trust level (strict, standard, trust)")
def init(source_path, target_stack, provider, trust_level):
    """Initialize modernization project."""
    state = get_state()

    # Parse target stack
    stack = []
    for part in target_stack.split(","):
        adapter, role = part.split(":")
        stack.append({"adapter": adapter, "role": role})

    state.init(source_path, stack, provider, trust_level)

    console.print(Panel(
        f"[bold green]Project initialized[/]\n\n"
        f"Source: {source_path}\n"
        f"Language: ColdFusion (auto-detected)\n"
        f"Target stack: {target_stack}\n"
        f"Provider: {provider}\n"
        f"Trust level: {trust_level}\n\n"
        f"[dim]State directory: .modernize/[/dim]",
        title="modernize init",
        border_style="green",
    ))
    console.print("[dim]Next step: modernize parse[/dim]")


# ── parse ─────────────────────────────────────────────────────────────

@cli.command()
def parse():
    """Step 1 — Parse legacy source to AST (deterministic, no AI)."""
    from pipeline.parser import run_parse
    run_parse(get_state())


# ── extract ───────────────────────────────────────────────────────────

@cli.command()
def extract():
    """Step 2 — Extract semantics from AST (mostly deterministic + targeted AI)."""
    from pipeline.extractor import run_extract
    run_extract(get_state())


# ── document ──────────────────────────────────────────────────────────

@cli.command()
def document():
    """Step 3 — Generate review documentation from semantic model."""
    from pipeline.documenter import run_document
    run_document(get_state())


# ── review ────────────────────────────────────────────────────────────

@cli.group()
def review():
    """Review pipeline artifacts."""
    pass


@review.command("semantics")
@click.argument("module", required=False)
def review_semantics(module):
    """Step 4 — Review extracted semantics (interactive)."""
    from pipeline.reviewer import run_review
    run_review(get_state(), module)


@review.command("architect")
def review_architect_cmd():
    """Review architecture decisions."""
    from pipeline.architect import run_review_architect
    run_review_architect(get_state())


@review.command("generate")
@click.argument("service")
def review_generate(service):
    """Review generated code for a service."""
    state = get_state()
    migration = state.load()
    gen = migration["pipeline"]["steps"]["generate"]["services"].get(service, {})
    if gen.get("status") != "completed":
        console.print(f"[red]Error:[/] Code not generated for {service}.")
        return
    console.print(f"[bold]Generated code for {service}:[/]")
    path = state.modernize_dir / "services" / service
    if path.exists():
        for layer_dir in sorted(path.iterdir()):
            if layer_dir.is_dir():
                console.print(f"\n  [{layer_dir.name}]")
                for f in sorted(layer_dir.rglob("*")):
                    if f.is_file():
                        rel = f.relative_to(path)
                        console.print(f"    {rel}")
    console.print(f"\n[dim]To approve, proceed to: modernize verify {service}[/dim]")


# ── correct ───────────────────────────────────────────────────────────

@cli.command()
@click.argument("target")
@click.option("--field", required=True, help="Field to correct (e.g. businessRule.description)")
@click.option("--value", required=True, help="New value")
def correct(target, field, value):
    """Correct an AI-generated semantic extraction."""
    from pipeline.reviewer import run_correct
    run_correct(get_state(), target, field, value)


# ── approve ───────────────────────────────────────────────────────────

@cli.group()
def approve():
    """Approve pipeline artifacts."""
    pass


@approve.command("semantics")
@click.argument("module", required=False)
@click.option("--all", "approve_all", is_flag=True, help="Approve all modules")
def approve_semantics(module, approve_all):
    """Approve semantic extractions for a module (or all)."""
    from pipeline.reviewer import run_approve
    run_approve(get_state(), module, approve_all)


@approve.command("architect")
def approve_architect():
    """Approve architecture decisions."""
    from pipeline.architect import run_approve_architect
    run_approve_architect(get_state())


# ── lock ──────────────────────────────────────────────────────────────

@cli.group()
def lock():
    """Lock approved mappings."""
    pass


@lock.command("semantics")
def lock_semantics():
    """Step 5a — Lock approved semantic mappings (immutable contract)."""
    from pipeline.locker import run_lock_semantics
    run_lock_semantics(get_state())


@lock.command("architecture")
def lock_architecture():
    """Step 5d — Lock architecture decisions."""
    from pipeline.locker import run_lock_architecture
    run_lock_architecture(get_state())


# ── architect ─────────────────────────────────────────────────────────

@cli.command()
def architect():
    """Step 5b — Design target architecture from locked semantics."""
    from pipeline.architect import run_architect
    run_architect(get_state())


# ── generate ──────────────────────────────────────────────────────────

@cli.command()
@click.argument("service")
def generate(service):
    """Step 6 — Generate target code from locked mappings."""
    from pipeline.generator import run_generate
    run_generate(get_state(), service)


# ── verify ────────────────────────────────────────────────────────────

@cli.command()
@click.argument("service")
def verify(service):
    """Verify behavioral equivalence for a service."""
    from pipeline.verifier import run_verify
    run_verify(get_state(), service)


# ── status ────────────────────────────────────────────────────────────

@cli.command()
def status():
    """Show project status and pipeline progress."""
    state = get_state()

    if not state.is_initialized:
        console.print("[red]No project initialized.[/] Run 'modernize init' first.")
        return

    migration = state.load()

    target_str = ", ".join(f"{t['adapter']} ({t['role']})" for t in migration["targetStack"])
    console.print(Panel(
        f"[bold]Project:[/] {migration['project']}\n"
        f"[bold]Source:[/] {migration['source']['language']} ({migration['source']['path']})\n"
        f"[bold]Target:[/] {target_str}\n"
        f"[bold]Provider:[/] {migration['provider']}\n"
        f"[bold]Trust level:[/] {migration['trustLevel']}",
        title="Project Status",
        border_style="blue",
    ))

    # Pipeline progress
    step_labels = {
        "parse": "1. Parse AST",
        "extract": "2. Extract Semantics",
        "document": "3. Generate Docs",
        "review": "4. Review",
        "lock_semantics": "5a. Lock Semantics",
        "architect": "5b. Architecture",
        "lock_architecture": "5d. Lock Architecture",
        "generate": "6. Generate Code",
        "verify": "7. Verify",
    }

    table = Table(title="Pipeline Progress", show_header=True, header_style="bold")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("AI Usage", style="dim")

    ai_usage = {
        "parse": "None",
        "extract": "Minimal",
        "document": "Minimal",
        "review": "None (human)",
        "lock_semantics": "None",
        "architect": "Moderate",
        "lock_architecture": "None",
        "generate": "Heavy",
        "verify": "Light",
    }

    steps = migration["pipeline"]["steps"]
    for key, label in step_labels.items():
        step_status = steps.get(key, {}).get("status", "pending")
        if step_status == "completed":
            status_str = "[green]completed[/]"
        elif step_status == "pending":
            status_str = "[dim]pending[/dim]"
        else:
            status_str = f"[yellow]{step_status}[/]"
        table.add_row(label, status_str, ai_usage.get(key, "—"))

    console.print(table)

    # Service groups
    if migration.get("serviceGroups"):
        console.print()
        sg_table = Table(title="Service Groups", show_header=True, header_style="bold")
        sg_table.add_column("Service", style="cyan")
        sg_table.add_column("Modules")
        sg_table.add_column("Status")

        for sg in migration["serviceGroups"]:
            sg_status = sg.get("status", "pending")
            if sg_status == "locked":
                status_str = "[green]locked[/]"
            else:
                status_str = f"[yellow]{sg_status}[/]"
            sg_table.add_row(sg["name"], ", ".join(sg["modules"]), status_str)

        console.print(sg_table)


# ── audit ─────────────────────────────────────────────────────────────

@cli.command()
def audit():
    """Show AI API call audit trail."""
    console.print(Panel(
        "[bold]Audit Trail[/]\n\n"
        "[dim]In the production tool, this shows every AI API call:\n"
        "timestamp, stage, what was sent (sanitized), what was redacted,\n"
        "which AI provider, and response summary.\n\n"
        "Mock tool: no real AI calls were made.[/dim]",
        title="modernize audit",
        border_style="blue",
    ))


if __name__ == "__main__":
    cli()
