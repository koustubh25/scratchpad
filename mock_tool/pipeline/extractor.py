"""Step 2 — Extract Semantics (Mostly Deterministic + Targeted AI)."""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

from core.state import ProjectState
from mock_data.semantic_data import ALL_SEMANTICS

console = Console()


def run_extract(state: ProjectState):
    """Extract semantic model from AST."""
    if state.get_step_status("parse") != "completed":
        console.print("[red]Error:[/] AST not parsed yet. Run 'modernize parse' first.")
        return

    console.print(Panel(
        "[bold]Step 2 — Extract Semantics[/]\n"
        "Walking AST to extract structured semantic facts.\n"
        "[dim]Deterministic extraction + targeted AI for business rules only.[/dim]",
        title="modernize extract",
        border_style="blue",
    ))

    modules = list(ALL_SEMANTICS.keys())
    ai_calls = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting semantics...", total=len(modules))

        for name in modules:
            # Phase 1: deterministic extraction
            progress.update(task, description=f"[cyan]{name}[/] — extracting signatures, queries, dependencies...")
            time.sleep(0.5)

            # Phase 2: AI for business rules
            semantics = ALL_SEMANTICS[name]()
            ai_items = [
                f for f in semantics["functions"]
                if f["businessRule"]["source"] == "ai"
            ]
            if ai_items:
                for fn in ai_items:
                    progress.update(
                        task,
                        description=f"[cyan]{name}[/] — [yellow]AI:[/] extracting business rule for {fn['name']}()..."
                    )
                    time.sleep(0.8)
                    ai_calls += 1

            state.write_artifact("semantics", f"{name}.semantic.json", semantics)
            progress.advance(task)

    # Write cross-module relationships
    cross_module = {
        "dependencyGraph": {
            "login": {"depends_on": ["UserService"]},
            "UserService": {"depends_on": []},
            "OrderService": {"depends_on": []},
        },
        "tableOwnership": {
            "users": ["UserService"],
            "orders": ["OrderService"],
            "order_items": ["OrderService"],
            "products": ["OrderService"],
        },
        "sharedState": {
            "session.userId": {"writtenBy": ["UserService"], "readBy": ["login"]},
            "session.userRole": {"writtenBy": ["UserService"], "readBy": []},
            "session.userEmail": {"writtenBy": ["UserService", "UserService.updateProfile"], "readBy": []},
        },
    }
    state.write_artifact("semantics", "cross-module.json", cross_module)

    console.print()

    # Summary table
    table = Table(title="Extraction Summary", show_header=True, header_style="bold")
    table.add_column("Module", style="cyan")
    table.add_column("Functions")
    table.add_column("Tables")
    table.add_column("AI-Extracted Items", style="yellow")
    table.add_column("Complexity")

    for name in modules:
        sem = ALL_SEMANTICS[name]()
        ai_count = sum(1 for f in sem["functions"] if f["businessRule"]["source"] == "ai")
        complexity_color = {"low": "green", "medium": "yellow", "high": "red"}.get(sem["complexity"], "white")
        table.add_row(
            name,
            str(len(sem["functions"])),
            ", ".join(sem["tables"]) if sem["tables"] else "—",
            str(ai_count),
            f"[{complexity_color}]{sem['complexity']}[/]",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]AI calls made: {ai_calls} (business rule extraction only)[/dim]")
    console.print(f"[dim]Artifacts written to .modernize/semantics/[/dim]")
    console.print(f"[dim]Next step: modernize document[/dim]")

    state.update_step("extract", "completed", modulesCount=len(modules), aiCalls=ai_calls)
