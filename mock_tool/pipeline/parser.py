"""Step 1 — Parse Code to AST (Fully Deterministic)."""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.panel import Panel

from core.state import ProjectState
from core.models import to_dict
from mock_data.ast_data import ALL_ASTS

console = Console()


def run_parse(state: ProjectState):
    """Parse all source files to AST."""
    if not state.is_initialized:
        console.print("[red]Error:[/] Project not initialized. Run 'modernize init' first.")
        return

    if state.get_step_status("parse") == "completed":
        console.print("[yellow]Warning:[/] AST already parsed. Re-parsing will overwrite.")

    migration = state.load()
    source_path = migration["source"]["path"]

    console.print(Panel(
        "[bold]Step 1 — Parse Code to AST[/]\n"
        "Deterministic parsing of legacy source into structured AST.\n"
        "[dim]No AI involved — fully local.[/dim]",
        title="modernize parse",
        border_style="blue",
    ))

    files_parsed = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting source files...", total=None)
        time.sleep(0.8)

        progress.update(task, description=f"Source: {source_path} (ColdFusion detected)")
        time.sleep(0.5)

        for name, ast_fn in ALL_ASTS.items():
            progress.update(task, description=f"Parsing {ast_fn().file}...")
            time.sleep(0.6)

            ast = ast_fn()
            ast_dict = to_dict(ast)
            filename = f"{ast.file}.ast.json"
            state.write_artifact("ast", filename, ast_dict)
            files_parsed.append(ast)

        progress.update(task, description="AST generation complete.")
        time.sleep(0.3)

    console.print()
    console.print(f"[green]Parsed {len(files_parsed)} files to AST[/]\n")

    for ast in files_parsed:
        tree = _build_ast_tree(ast)
        console.print(tree)
        console.print()

    state.update_step("parse", "completed", filesCount=len(files_parsed))

    console.print(f"[dim]Artifacts written to .modernize/ast/[/dim]")
    console.print(f"[dim]Next step: modernize extract[/dim]")


def _build_ast_tree(ast) -> Tree:
    label = f"[bold]{ast.file}[/bold]"
    if ast.type == "component":
        label += f"  [dim](component: {ast.name}"
        if ast.extends:
            label += f", extends: {ast.extends}"
        label += ")[/dim]"
    else:
        label += f"  [dim](template)[/dim]"

    tree = Tree(label)

    if ast.properties:
        props = tree.add("[cyan]Properties[/]")
        for p in ast.properties:
            props.add(f"{p['name']}: {p['type']} [dim]({p['scope']})[/dim]")

    for fn in ast.functions:
        args_str = ", ".join(f"{a.name}: {a.type}" for a in fn.arguments)
        fn_label = f"[yellow]{fn.name}[/]({args_str}) → {fn.return_type}"
        fn_node = tree.add(fn_label)

        if fn.queries:
            q_node = fn_node.add("[magenta]Queries[/]")
            for q in fn.queries:
                q_label = f"{q.name}: {q.operation} {', '.join(q.tables)}"
                if q.parameterized:
                    q_label += " [green](parameterized)[/green]"
                q_node.add(q_label)

        if fn.conditionals:
            c_node = fn_node.add("[red]Conditionals[/]")
            for c in fn.conditionals:
                c_node.add(f"{c.condition} → {c.action}")

        if fn.scope_writes:
            s_node = fn_node.add("[blue]State Writes[/]")
            for s in fn.scope_writes:
                s_node.add(f"{s.scope}.{s.key}")

        if fn.function_calls:
            call_node = fn_node.add("[dim]Calls[/]")
            for fc in fn.function_calls:
                call_node.add(fc.target)

    return tree
