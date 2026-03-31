"""Step 4 — Review with Original Developers (Interactive)."""

import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from core.state import ProjectState
from mock_data.semantic_data import ALL_SEMANTICS

console = Console()


def run_review(state: ProjectState, module_name: str = None):
    """Interactive review of extracted semantics."""
    if state.get_step_status("extract") != "completed":
        console.print("[red]Error:[/] Semantics not extracted yet. Run 'modernize extract' first.")
        return

    console.print(Panel(
        "[bold]Step 4 — Review Semantics[/]\n"
        "Review extracted semantic facts. Confirm or correct AI-generated items.\n"
        "[dim]Only AI-extracted items need review. Deterministic extractions are verified from AST.[/dim]",
        title="modernize review semantics",
        border_style="blue",
    ))

    migration = state.load()
    review_state = migration["pipeline"]["steps"]["review"].get("modules", {})

    if module_name:
        if module_name not in ALL_SEMANTICS:
            console.print(f"[red]Error:[/] Unknown module '{module_name}'. Available: {', '.join(ALL_SEMANTICS.keys())}")
            return
        _review_module(state, module_name, review_state)
    else:
        _show_review_status(review_state)


def _show_review_status(review_state: dict):
    """Show review status for all modules."""
    table = Table(title="Review Status", show_header=True, header_style="bold")
    table.add_column("Module", style="cyan")
    table.add_column("Items to Review")
    table.add_column("Status")
    table.add_column("Corrections")

    for name in ALL_SEMANTICS:
        sem = ALL_SEMANTICS[name]()
        ai_items = sum(1 for f in sem["functions"] if f["businessRule"]["source"] == "ai")
        mod_state = review_state.get(name, {})
        status = mod_state.get("status", "pending")
        corrections = mod_state.get("corrections_count", 0)

        if status == "approved":
            status_str = "[green]approved[/]"
        elif status == "reviewed":
            status_str = "[yellow]reviewed (not yet approved)[/]"
        else:
            status_str = "[red]pending[/]"

        table.add_row(
            name,
            f"{ai_items} AI-generated" if ai_items else "[green]all deterministic[/green]",
            status_str,
            str(corrections) if corrections else "—",
        )

    console.print(table)
    console.print()
    console.print("[dim]To review a specific module: modernize review semantics <module>[/dim]")
    console.print("[dim]To approve: modernize approve semantics <module>[/dim]")


def _review_module(state: ProjectState, module_name: str, review_state: dict):
    """Interactive review of a single module."""
    sem = ALL_SEMANTICS[module_name]()
    ai_functions = [f for f in sem["functions"] if f["businessRule"]["source"] == "ai"]

    if not ai_functions:
        console.print(f"[green]{module_name}[/] — all extractions are deterministic. No review needed.")
        console.print("[dim]You can still approve it: modernize approve semantics {module_name}[/dim]")
        return

    console.print(f"\n[bold cyan]{module_name}[/] — {len(ai_functions)} items need review\n")

    corrections = []
    additions = []

    for i, fn in enumerate(ai_functions, 1):
        br = fn["businessRule"]
        console.print(Panel(
            f"[bold]Function:[/] {fn['name']}()\n"
            f"[bold]AI Extraction:[/] \"{br['name']}\"\n"
            f"[bold]Description:[/] {br['description']}\n"
            f"[bold]Confidence:[/] {br['confidence']}%\n"
            f"\n[dim]Control flow:[/dim]",
            title=f"Review Item {i}/{len(ai_functions)}",
            border_style="yellow",
        ))

        if fn.get("controlFlow"):
            for cf in fn["controlFlow"]:
                console.print(f"  - If {cf['condition']} → {cf['action']}")

        console.print()
        choice = Prompt.ask(
            "Is this extraction correct?",
            choices=["correct", "edit", "missing", "skip"],
            default="correct",
        )

        if choice == "edit":
            new_desc = Prompt.ask("Enter corrected description", default=br["description"])
            corrections.append({
                "function": fn["name"],
                "field": "businessRule.description",
                "original": br["description"],
                "corrected": new_desc,
                "by": "reviewer",
                "at": datetime.now().isoformat(),
            })
            console.print(f"[yellow]Correction recorded for {fn['name']}()[/]")

        elif choice == "missing":
            missing_desc = Prompt.ask("What's missing?")
            additions.append({
                "function": fn["name"],
                "addition": missing_desc,
                "by": "reviewer",
                "at": datetime.now().isoformat(),
            })
            console.print(f"[yellow]Addition recorded for {fn['name']}()[/]")

        elif choice == "correct":
            console.print(f"[green]Confirmed {fn['name']}()[/]")

        console.print()

    # Save corrections
    if corrections or additions:
        correction_data = {
            "module": module_name,
            "reviewedAt": datetime.now().isoformat(),
            "corrections": corrections,
            "additions": additions,
        }
        state.write_artifact("corrections", f"{module_name}.corrections.json", correction_data)

    # Update review state
    migration = state.load()
    migration["pipeline"]["steps"]["review"]["modules"][module_name] = {
        "status": "reviewed",
        "reviewedAt": datetime.now().isoformat(),
        "corrections_count": len(corrections),
        "additions_count": len(additions),
    }
    state.save(migration)

    console.print(f"[green]Review complete for {module_name}[/]")
    console.print(f"  Corrections: {len(corrections)}")
    console.print(f"  Additions: {len(additions)}")
    console.print(f"\n[dim]To approve: modernize approve semantics {module_name}[/dim]")


def run_correct(state: ProjectState, target: str, field: str, value: str):
    """Apply a correction to a semantic extraction."""
    parts = target.split(".")
    if len(parts) != 2:
        console.print("[red]Error:[/] Target must be in format: ModuleName.functionName")
        return

    module_name, func_name = parts
    correction = {
        "function": func_name,
        "field": field,
        "corrected": value,
        "by": "reviewer",
        "at": datetime.now().isoformat(),
    }

    existing = state.read_artifact("corrections", f"{module_name}.corrections.json")
    if existing:
        existing["corrections"].append(correction)
    else:
        existing = {
            "module": module_name,
            "reviewedAt": datetime.now().isoformat(),
            "corrections": [correction],
            "additions": [],
        }

    state.write_artifact("corrections", f"{module_name}.corrections.json", existing)
    console.print(f"[green]Correction applied:[/] {module_name}.{func_name}.{field} = \"{value}\"")


def run_approve(state: ProjectState, module_name: str = None, approve_all: bool = False):
    """Approve module semantics."""
    if approve_all:
        modules = list(ALL_SEMANTICS.keys())
    elif module_name:
        modules = [module_name]
    else:
        console.print("[red]Error:[/] Specify a module name or use --all")
        return

    migration = state.load()

    for name in modules:
        if name not in ALL_SEMANTICS:
            console.print(f"[red]Error:[/] Unknown module '{name}'")
            continue

        migration["pipeline"]["steps"]["review"]["modules"][name] = {
            **migration["pipeline"]["steps"]["review"]["modules"].get(name, {}),
            "status": "approved",
            "approvedAt": datetime.now().isoformat(),
            "approvedBy": "reviewer",
        }
        console.print(f"[green]Approved:[/] {name}")

    # Check if all approved
    all_approved = all(
        migration["pipeline"]["steps"]["review"]["modules"].get(m, {}).get("status") == "approved"
        for m in ALL_SEMANTICS
    )

    state.save(migration)

    if all_approved:
        state.update_step("review", "completed")
        console.print(f"\n[bold green]All modules approved.[/] Ready to lock.")
        console.print(f"[dim]Next step: modernize lock semantics[/dim]")
    else:
        pending = [
            m for m in ALL_SEMANTICS
            if migration["pipeline"]["steps"]["review"]["modules"].get(m, {}).get("status") != "approved"
        ]
        console.print(f"\n[yellow]Still pending approval:[/] {', '.join(pending)}")
