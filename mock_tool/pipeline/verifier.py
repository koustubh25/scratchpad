"""Post-Step 6 — Verify behavioral equivalence."""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from core.state import ProjectState

console = Console()

MOCK_VERIFICATION = {
    "users-service": {
        "endpoints": [
            {"endpoint": "POST /api/auth/login", "source": "authenticate", "status": "PASS",
             "detail": "Response structure matches. JWT token replaces session correctly."},
            {"endpoint": "POST /api/auth/login (locked)", "source": "authenticate", "status": "PASS",
             "detail": "Account lockout triggers after 3 failures. 30-min window verified."},
            {"endpoint": "GET /api/users/:id", "source": "getUserById", "status": "PASS",
             "detail": "All fields mapped correctly. Date format differs (ISO 8601 vs CF)."},
            {"endpoint": "PUT /api/users/:id/profile", "source": "updateProfile", "status": "PASS",
             "detail": "Duplicate email check works. Session email sync replaced by JWT re-issue."},
        ],
        "mappingConformance": [
            {"rule": "User Authentication", "status": "CONFORMS", "detail": "All control flow paths implemented."},
            {"rule": "Profile Update", "status": "CONFORMS", "detail": "Duplicate email validation + conditional email sync present."},
        ],
        "verdict": "PASS",
    },
    "orders-service": {
        "endpoints": [
            {"endpoint": "POST /api/orders", "source": "createOrder", "status": "PASS",
             "detail": "Stock validation, bulk discount, transactional insert verified."},
            {"endpoint": "GET /api/orders", "source": "getOrdersByUser", "status": "PASS",
             "detail": "Item count aggregation matches. Sort order: DESC by created_at."},
            {"endpoint": "POST /api/orders/:id/cancel", "source": "cancelOrder", "status": "NEEDS REVIEW",
             "detail": "Stock restoration works. Race condition possible under concurrent cancellations — original CF had same issue."},
        ],
        "mappingConformance": [
            {"rule": "Order Creation", "status": "CONFORMS", "detail": "5% discount at $10K threshold verified."},
            {"rule": "Order Cancellation", "status": "CONFORMS", "detail": "Ownership + status checks present. Stock restoration in transaction."},
        ],
        "verdict": "PASS (with notes)",
    },
}


def run_verify(state: ProjectState, service_name: str):
    """Verify behavioral equivalence for a service."""
    migration = state.load()
    gen_status = migration["pipeline"]["steps"]["generate"]["services"].get(service_name, {})
    if gen_status.get("status") != "completed":
        console.print(f"[red]Error:[/] Code not generated for {service_name}. Run 'modernize generate {service_name}' first.")
        return

    if service_name not in MOCK_VERIFICATION:
        console.print(f"[red]Error:[/] No verification data for '{service_name}'")
        return

    console.print(Panel(
        f"[bold]Verify — {service_name}[/]\n"
        "Checking behavioral equivalence + locked mapping conformance.\n"
        "[dim]Compares legacy behavior against generated code using locked mappings as reference.[/dim]",
        title=f"modernize verify {service_name}",
        border_style="blue",
    ))

    verification = MOCK_VERIFICATION[service_name]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running verification...", total=None)

        progress.update(task, description="Recording legacy behavior (mock)...")
        time.sleep(0.8)

        progress.update(task, description="Replaying against generated code...")
        time.sleep(1.0)

        progress.update(task, description="Comparing outputs...")
        time.sleep(0.6)

        progress.update(task, description="Checking locked mapping conformance...")
        time.sleep(0.5)

    console.print()

    # Behavioral equivalence table
    table = Table(title="Behavioral Equivalence", show_header=True, header_style="bold")
    table.add_column("Endpoint")
    table.add_column("Source")
    table.add_column("Status")
    table.add_column("Detail", style="dim", max_width=55)

    for ep in verification["endpoints"]:
        status = ep["status"]
        if status == "PASS":
            status_str = "[green]PASS[/]"
        elif status == "NEEDS REVIEW":
            status_str = "[yellow]NEEDS REVIEW[/]"
        else:
            status_str = "[red]FAIL[/]"
        table.add_row(ep["endpoint"], ep["source"], status_str, ep["detail"])

    console.print(table)
    console.print()

    # Mapping conformance table
    table2 = Table(title="Locked Mapping Conformance", show_header=True, header_style="bold")
    table2.add_column("Business Rule")
    table2.add_column("Status")
    table2.add_column("Detail", style="dim")

    for mc in verification["mappingConformance"]:
        status_str = "[green]CONFORMS[/]" if mc["status"] == "CONFORMS" else "[red]DIVERGES[/]"
        table2.add_row(mc["rule"], status_str, mc["detail"])

    console.print(table2)
    console.print()

    # Verdict
    verdict = verification["verdict"]
    if "PASS" in verdict and "notes" not in verdict.lower():
        console.print(f"[bold green]Verdict: {verdict}[/]")
    elif "PASS" in verdict:
        console.print(f"[bold yellow]Verdict: {verdict}[/]")
    else:
        console.print(f"[bold red]Verdict: {verdict}[/]")

    # Save report
    state.write_artifact(f"recordings/{service_name}", "verification-report.json", verification)
    migration = state.load()
    migration["pipeline"]["steps"]["verify"]["services"][service_name] = {
        "status": "completed",
        "verdict": verdict,
    }
    state.save(migration)

    console.print()
    console.print(f"[dim]Report: .modernize/recordings/{service_name}/verification-report.json[/dim]")
