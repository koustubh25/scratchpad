"""Step 5b — Design Architecture (from Locked Semantics)."""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from core.state import ProjectState
from mock_data.architecture_data import (
    get_architecture, get_blueprint_index_md,
    get_service_blueprint_md, get_cross_cutting_md,
)

console = Console()


def run_architect(state: ProjectState):
    """Design target architecture from locked semantic mappings."""
    if state.get_step_status("lock_semantics") != "completed":
        console.print("[red]Error:[/] Semantics not locked. Run 'modernize lock semantics' first.")
        return

    console.print(Panel(
        "[bold]Step 5b — Design Architecture[/]\n"
        "Analyzing locked semantic mappings to design target architecture.\n"
        "[dim]AI: service grouping, API contracts, component routing.[/dim]",
        title="modernize architect",
        border_style="blue",
    ))

    arch = get_architecture()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing dependencies...", total=None)
        time.sleep(1.0)

        progress.update(task, description="[yellow]AI:[/] Grouping modules into service boundaries...")
        time.sleep(1.5)

        progress.update(task, description="[yellow]AI:[/] Defining API contracts...")
        time.sleep(1.0)

        progress.update(task, description="[yellow]AI:[/] Routing components to stack layers...")
        time.sleep(0.8)

        progress.update(task, description="Generating architecture blueprint (index)...")
        time.sleep(0.3)

        for sg in arch["serviceGroups"]:
            progress.update(task, description=f"Generating blueprint for {sg['name']}...")
            time.sleep(0.5)

        progress.update(task, description="Generating cross-cutting concerns...")
        time.sleep(0.3)

        progress.update(task, description="Generating translation spec...")
        time.sleep(0.3)

    # Save artifacts — multiple files for iterative review
    state.write_artifact("architecture", "architecture-decisions.json", arch)

    # Index (top-level summary with links to per-service docs)
    state.write_artifact("architecture", "architecture-blueprint.md", get_blueprint_index_md(), as_json=False)

    # Per-service-group docs (reviewable independently)
    for sg in arch["serviceGroups"]:
        state.write_artifact(
            "architecture/services",
            f"{sg['name']}.md",
            get_service_blueprint_md(sg["name"]),
            as_json=False,
        )

    # Cross-cutting concerns (state mapping, risks, infra)
    state.write_artifact("architecture", "cross-cutting.md", get_cross_cutting_md(), as_json=False)

    console.print()

    # Service boundaries
    table = Table(title="Service Boundaries", show_header=True, header_style="bold")
    table.add_column("Service", style="cyan")
    table.add_column("Modules")
    table.add_column("Tables")
    table.add_column("Rationale", style="dim", max_width=50)

    for sg in arch["serviceGroups"]:
        table.add_row(
            sg["name"],
            ", ".join(sg["modules"]),
            ", ".join(sg["sharedTables"]),
            sg["reason"],
        )

    console.print(table)
    console.print()

    # API contracts
    table2 = Table(title="API Contracts", show_header=True, header_style="bold")
    table2.add_column("Service", style="cyan")
    table2.add_column("Endpoint")
    table2.add_column("Source Mapping", style="dim")

    for contract in arch["apiContracts"]:
        for endpoint in contract["endpoints"]:
            table2.add_row(
                contract["service"],
                endpoint["path"],
                endpoint["source"],
            )

    console.print(table2)
    console.print()

    # Component routing
    table3 = Table(title="Component Routing", show_header=True, header_style="bold")
    table3.add_column("Legacy", style="yellow")
    table3.add_column("→", justify="center")
    table3.add_column("Target", style="green")
    table3.add_column("Layer")
    table3.add_column("Agent")

    for r in arch["componentRouting"]:
        table3.add_row(
            r["source"], "→", r["target"], r["stackLayer"], r["agent"]
        )

    console.print(table3)
    console.print()

    # State mapping
    console.print("[bold]State Mapping:[/]")
    for legacy, modern in arch["dataMapping"].items():
        console.print(f"  {legacy} → {modern}")
    console.print()

    state.update_step("architect", "completed")

    console.print("[bold]Review Documents Generated:[/]")
    console.print(f"  .modernize/architecture/architecture-blueprint.md  [dim](start here — summary + links)[/dim]")
    for sg in arch["serviceGroups"]:
        console.print(f"  .modernize/architecture/services/{sg['name']}.md  [dim](review independently)[/dim]")
    console.print(f"  .modernize/architecture/cross-cutting.md  [dim](state mapping, risks, infra)[/dim]")
    console.print()
    console.print(f"[dim]Next step: modernize review architect → modernize approve architect → modernize lock architecture[/dim]")


def run_review_architect(state: ProjectState):
    """Review architecture decisions."""
    if state.get_step_status("architect") != "completed":
        console.print("[red]Error:[/] Architecture not yet designed. Run 'modernize architect' first.")
        return

    console.print(Panel(
        "[bold]Architecture Review[/]\n"
        "Review each document independently. Each service group has its own doc.\n"
        "[dim]Start with the index, then review per-service docs, then cross-cutting.[/dim]",
        title="modernize review architect",
        border_style="blue",
    ))

    arch = state.read_artifact("architecture", "architecture-decisions.json")

    review_table = Table(title="Review Documents", show_header=True, header_style="bold")
    review_table.add_column("Document", style="cyan")
    review_table.add_column("Contents")
    review_table.add_column("Status")

    review_table.add_row(
        "architecture-blueprint.md",
        "Summary + service boundaries + migration order",
        "[yellow]pending[/]",
    )
    for sg in arch["serviceGroups"]:
        module_count = len(sg["modules"])
        endpoint_count = sum(
            len(c["endpoints"]) for c in arch["apiContracts"] if c["service"] == sg["name"]
        )
        review_table.add_row(
            f"services/{sg['name']}.md",
            f"{module_count} modules, {endpoint_count} endpoints, business rules, risks",
            "[yellow]pending[/]",
        )
    review_table.add_row(
        "cross-cutting.md",
        "State mapping, risk register, infrastructure",
        "[yellow]pending[/]",
    )

    console.print(review_table)
    console.print()
    console.print("[dim]To approve: modernize approve architect[/dim]")


def run_approve_architect(state: ProjectState):
    """Approve architecture decisions."""
    if state.get_step_status("architect") != "completed":
        console.print("[red]Error:[/] Architecture not yet designed. Run 'modernize architect' first.")
        return

    state.update_step("architect", "completed", approvedAt=str(time.time()))
    console.print("[bold green]Architecture approved.[/]")
    console.print(f"[dim]Next step: modernize lock architecture[/dim]")
