"""Step 3 — Generate Documentation (Template-Driven from Semantic Model)."""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from core.state import ProjectState
from mock_data.semantic_data import ALL_SEMANTICS

console = Console()


def run_document(state: ProjectState):
    """Generate review documentation from semantic model."""
    if state.get_step_status("extract") != "completed":
        console.print("[red]Error:[/] Semantics not extracted yet. Run 'modernize extract' first.")
        return

    console.print(Panel(
        "[bold]Step 3 — Generate Documentation[/]\n"
        "Template-driven docs from structured semantic model.\n"
        "[dim]Minimal AI — natural language summaries from structured data.[/dim]",
        title="modernize document",
        border_style="blue",
    ))

    modules = list(ALL_SEMANTICS.keys())

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating docs...", total=None)

        for name in modules:
            progress.update(task, description=f"Generating doc for {name}...")
            sem = ALL_SEMANTICS[name]()
            doc = _generate_module_doc(sem)
            state.write_artifact("docs", f"{name}.md", doc, as_json=False)
            time.sleep(0.5)

        # Generate overview doc
        progress.update(task, description="Generating overview...")
        overview = _generate_overview(modules)
        state.write_artifact("docs", "overview.md", overview, as_json=False)
        time.sleep(0.3)

    console.print()
    console.print(f"[green]Generated {len(modules) + 1} documents[/]\n")

    for name in modules:
        sem = ALL_SEMANTICS[name]()
        ai_items = sum(1 for f in sem["functions"] if f["businessRule"]["source"] == "ai")
        status = f"[yellow]{ai_items} items need review[/]" if ai_items else "[green]all deterministic[/green]"
        console.print(f"  .modernize/docs/{name}.md — {status}")

    console.print(f"  .modernize/docs/overview.md")
    console.print()
    console.print(f"[dim]Next step: modernize review semantics[/dim]")

    state.update_step("document", "completed")


def _generate_module_doc(sem: dict) -> str:
    lines = []
    lines.append(f"# Module: {sem['module']}")
    lines.append(f"**Source:** `{sem['source']}`")
    lines.append(f"**Complexity:** {sem['complexity']}")
    lines.append("")

    # Functions table
    lines.append("## Functions")
    lines.append("")
    lines.append("| Name | Business Rule | Confidence | Source |")
    lines.append("|------|--------------|------------|--------|")
    for fn in sem["functions"]:
        br = fn["businessRule"]
        source_tag = f"**[AI]**" if br["source"] == "ai" else "deterministic"
        lines.append(f"| `{fn['name']}` | {br['name']} | {br['confidence']}% | {source_tag} |")
    lines.append("")

    # Data access
    all_access = []
    for fn in sem["functions"]:
        for da in fn.get("dataAccess", []):
            all_access.append((fn["name"], da))

    if all_access:
        lines.append("## Data Access")
        lines.append("")
        lines.append("| Function | Table | Operation | Parameterized |")
        lines.append("|----------|-------|-----------|---------------|")
        for fn_name, da in all_access:
            table = da.get("table", "—")
            op = da.get("operation", "—")
            param = "Yes" if da.get("parameterized") else "No"
            lines.append(f"| `{fn_name}` | {table} | {op} | {param} |")
        lines.append("")

    # State writes
    all_state = []
    for fn in sem["functions"]:
        for sw in fn.get("stateWrites", []):
            all_state.append((fn["name"], sw))

    if all_state:
        lines.append("## State Writes")
        lines.append("")
        for fn_name, sw in all_state:
            cond = f" *(condition: {sw['condition']})*" if sw.get("condition") else ""
            lines.append(f"- `{fn_name}` writes `{sw['scope']}.{sw['key']}`{cond}")
        lines.append("")

    # Dependencies
    if sem.get("dependencies"):
        lines.append("## Dependencies")
        lines.append("")
        for dep in sem["dependencies"]:
            lines.append(f"- Depends on: `{dep}`")
        lines.append("")

    # Control flow per function
    lines.append("## Business Rules (Detail)")
    lines.append("")
    for fn in sem["functions"]:
        br = fn["businessRule"]
        tag = " :warning: **AI-generated — needs review**" if br["source"] == "ai" else ""
        lines.append(f"### `{fn['name']}()`{tag}")
        lines.append("")
        lines.append(f"**Rule:** {br['name']}")
        lines.append(f"**Description:** {br['description']}")
        lines.append(f"**Confidence:** {br['confidence']}%")
        lines.append("")

        if fn.get("controlFlow"):
            lines.append("**Control Flow:**")
            for cf in fn["controlFlow"]:
                lines.append(f"- If {cf['condition']} → {cf['action']}")
            lines.append("")

        if fn.get("calls"):
            lines.append(f"**Calls:** {', '.join(f'`{c}`' for c in fn['calls'])}")
            lines.append("")

        if fn.get("calledBy"):
            lines.append(f"**Called by:** {', '.join(f'`{c}`' for c in fn['calledBy'])}")
            lines.append("")

    # Items needing review
    review_items = [f for f in sem["functions"] if f["businessRule"]["source"] == "ai"]
    if review_items:
        lines.append("---")
        lines.append("")
        lines.append("## Items Needing Review")
        lines.append("")
        for fn in review_items:
            lines.append(f"- [ ] `{fn['name']}()` — \"{fn['businessRule']['name']}\" "
                         f"(AI-generated, {fn['businessRule']['confidence']}% confidence)")
        lines.append("")

    return "\n".join(lines)


def _generate_overview(modules: list[str]) -> str:
    lines = [
        "# Extraction Overview",
        "",
        f"**Modules analyzed:** {len(modules)}",
        f"**Source language:** ColdFusion",
        "",
        "## Modules",
        "",
    ]
    for name in modules:
        sem = ALL_SEMANTICS[name]()
        ai_count = sum(1 for f in sem["functions"] if f["businessRule"]["source"] == "ai")
        lines.append(f"- **{name}** ({sem['source']}) — {len(sem['functions'])} functions, "
                     f"{ai_count} AI-extracted rules, complexity: {sem['complexity']}")
    lines.append("")
    lines.append("## Cross-Module Dependencies")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")
    lines.append('    login["login.cfm"] --> UserService["UserService.cfc"]')
    lines.append('    UserService -.->|"users table"| DB[(Database)]')
    lines.append('    OrderService["OrderService.cfc"] -.->|"orders, products tables"| DB')
    lines.append("```")
    lines.append("")
    return "\n".join(lines)
