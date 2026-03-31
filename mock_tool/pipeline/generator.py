"""Step 6 — Generate New Code (AI, from Locked Mappings)."""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm

from core.state import ProjectState
from mock_data.generated_code import (
    GENERATED_GO_USER_HANDLER,
    GENERATED_REACT_LOGIN,
    GENERATED_GO_ORDER_HANDLER,
)

console = Console()

SERVICE_CODE = {
    "users-service": {
        "backend": [
            ("handlers/user_handler.go", GENERATED_GO_USER_HANDLER, "logic"),
        ],
        "frontend": [
            ("src/pages/LoginPage.tsx", GENERATED_REACT_LOGIN, "ui"),
        ],
    },
    "orders-service": {
        "backend": [
            ("handlers/order_handler.go", GENERATED_GO_ORDER_HANDLER, "logic"),
        ],
        "frontend": [],
    },
}


def run_generate(state: ProjectState, service_name: str):
    """Generate code for a service group from locked mappings."""
    if state.get_step_status("lock_architecture") != "completed":
        console.print("[red]Error:[/] Architecture not locked. Run 'modernize lock architecture' first.")
        return

    if service_name not in SERVICE_CODE:
        available = ", ".join(SERVICE_CODE.keys())
        console.print(f"[red]Error:[/] Unknown service '{service_name}'. Available: {available}")
        return

    console.print(Panel(
        f"[bold]Step 6 — Generate Code for {service_name}[/]\n"
        "AI generates target code from locked semantic mappings.\n"
        "[dim]AI never sees legacy source — only locked mappings + target conventions.[/dim]",
        title=f"modernize generate {service_name}",
        border_style="blue",
    ))

    service = SERVICE_CODE[service_name]
    files_generated = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        total = sum(len(files) for files in service.values())
        task = progress.add_task("Generating...", total=total)

        for layer, files in service.items():
            if not files:
                continue

            for filename, code, agent in files:
                progress.update(
                    task,
                    description=f"[yellow]AI ({agent} agent):[/] generating {filename}..."
                )
                time.sleep(1.5)

                path = state.write_artifact(
                    f"services/{service_name}/{layer}",
                    filename,
                    code,
                    as_json=False,
                )
                files_generated.append((layer, filename, agent))
                progress.advance(task)

        # Generate wiring
        progress.update(task, description="Wiring frontend ↔ backend (API client)...")
        time.sleep(0.5)

    console.print()

    # Show generated files
    console.print(f"[bold green]Generated {len(files_generated)} files for {service_name}[/]\n")

    for layer, filename, agent in files_generated:
        console.print(f"  [{layer}] {filename} [dim](via {agent} agent)[/dim]")

    console.print()

    # Preview first file
    if files_generated:
        layer, filename, _ = files_generated[0]
        code = SERVICE_CODE[service_name][layer][0][1]
        lang = "go" if filename.endswith(".go") else "tsx"

        if Confirm.ask(f"Preview {filename}?", default=True):
            # Show first 40 lines
            preview_lines = code.strip().split("\n")[:40]
            preview = "\n".join(preview_lines)
            if len(code.strip().split("\n")) > 40:
                preview += "\n// ... (truncated)"
            syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
            console.print(syntax)
            console.print()

    # Update state
    migration = state.load()
    migration["pipeline"]["steps"]["generate"]["services"][service_name] = {
        "status": "completed",
        "filesGenerated": len(files_generated),
    }
    state.save(migration)

    console.print(f"[dim]Output: .modernize/services/{service_name}/[/dim]")
    console.print(f"[dim]Next step: modernize verify {service_name}[/dim]")
