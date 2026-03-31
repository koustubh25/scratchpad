"""Step 5a — Lock Approved Mappings (Deterministic Freeze)."""

import hashlib
import json
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.state import ProjectState
from mock_data.semantic_data import ALL_SEMANTICS

console = Console()


def run_lock_semantics(state: ProjectState):
    """Lock all approved semantic mappings."""
    if state.get_step_status("review") != "completed":
        console.print("[red]Error:[/] Not all modules approved. Run 'modernize approve semantics --all' first.")
        return

    console.print(Panel(
        "[bold]Step 5a — Lock Semantic Mappings[/]\n"
        "Freezing approved semantics as immutable contract.\n"
        "[dim]Checksums computed. Locked mappings cannot be modified without explicit unlock.[/dim]",
        title="modernize lock semantics",
        border_style="blue",
    ))

    time.sleep(0.5)

    # Build lock
    lock = {
        "lockVersion": "1.0",
        "lockedAt": datetime.now().isoformat(),
        "lockedBy": "modernize-cli",
        "modules": {},
    }

    for name in ALL_SEMANTICS:
        sem = ALL_SEMANTICS[name]()

        # Apply any corrections
        corrections = state.read_artifact("corrections", f"{name}.corrections.json")
        if corrections:
            for corr in corrections.get("corrections", []):
                # In real tool, this would modify the semantic model
                pass

        sem_json = json.dumps(sem, sort_keys=True, default=str)
        checksum = hashlib.sha256(sem_json.encode()).hexdigest()

        migration = state.load()
        mod_review = migration["pipeline"]["steps"]["review"]["modules"].get(name, {})

        lock["modules"][name] = {
            "status": "locked",
            "approvedBy": mod_review.get("approvedBy", "reviewer"),
            "approvedAt": mod_review.get("approvedAt", datetime.now().isoformat()),
            "semantics": sem,
            "corrections": corrections.get("corrections", []) if corrections else [],
            "checksum": f"sha256:{checksum[:16]}",
        }
        time.sleep(0.3)

    # Cross-module data
    cross_module = state.read_artifact("semantics", "cross-module.json")
    if cross_module:
        lock["crossModule"] = cross_module

    # Lock manifest
    manifest = {
        "lockType": "semantic",
        "version": "1.0",
        "lockedAt": lock["lockedAt"],
        "moduleCount": len(lock["modules"]),
        "checksums": {
            name: mod["checksum"] for name, mod in lock["modules"].items()
        },
    }

    state.write_artifact("locked", "semantic-lock.json", lock)
    state.write_artifact("locked", "lock-manifest.json", manifest)

    state.update_step("lock_semantics", "completed")

    # Display summary
    table = Table(title="Semantic Lock", show_header=True, header_style="bold")
    table.add_column("Module", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Checksum", style="dim")
    table.add_column("Corrections")

    for name, mod in lock["modules"].items():
        table.add_row(
            name,
            "LOCKED",
            mod["checksum"],
            str(len(mod["corrections"])) if mod["corrections"] else "—",
        )

    console.print(table)
    console.print()
    console.print("[bold green]Semantic mappings locked.[/]")
    console.print("[dim]These mappings are now immutable. To change, use: modernize unlock semantics[/dim]")
    console.print(f"[dim]Next step: modernize architect[/dim]")


def run_lock_architecture(state: ProjectState):
    """Lock architecture decisions."""
    if state.get_step_status("architect") != "completed":
        console.print("[red]Error:[/] Architecture not yet designed. Run 'modernize architect' first.")
        return

    migration = state.load()
    arch_review = migration["pipeline"]["steps"].get("architect", {})
    if arch_review.get("status") != "completed":
        console.print("[red]Error:[/] Architecture not yet approved. Run 'modernize approve architect' first.")
        return

    console.print(Panel(
        "[bold]Step 5d — Lock Architecture Decisions[/]\n"
        "Freezing service boundaries, API contracts, and component routing.\n"
        "[dim]Combined with semantic lock to form the complete generation contract.[/dim]",
        title="modernize lock architecture",
        border_style="blue",
    ))

    time.sleep(0.5)

    arch = state.read_artifact("architecture", "architecture-decisions.json")
    if not arch:
        console.print("[red]Error:[/] Architecture decisions not found.")
        return

    arch_json = json.dumps(arch, sort_keys=True, default=str)
    checksum = hashlib.sha256(arch_json.encode()).hexdigest()

    arch_lock = {
        "lockType": "architecture",
        "lockVersion": "1.0",
        "lockedAt": datetime.now().isoformat(),
        "lockedBy": "modernize-cli",
        "architecture": arch,
        "checksum": f"sha256:{checksum[:16]}",
    }

    state.write_artifact("locked", "architecture-lock.json", arch_lock)

    # Update manifest
    manifest = state.read_artifact("locked", "lock-manifest.json") or {}
    manifest["architectureLock"] = {
        "lockedAt": arch_lock["lockedAt"],
        "checksum": arch_lock["checksum"],
        "serviceGroups": len(arch["serviceGroups"]),
    }
    manifest["fullyLocked"] = True
    state.write_artifact("locked", "lock-manifest.json", manifest)

    state.update_step("lock_architecture", "completed")

    # Update service groups in migration state
    migration = state.load()
    migration["serviceGroups"] = [
        {"name": sg["name"], "modules": sg["modules"], "status": "locked"}
        for sg in arch["serviceGroups"]
    ]
    state.save(migration)

    console.print("[bold green]Architecture locked.[/]")
    console.print()

    table = Table(title="Locked Service Groups", show_header=True, header_style="bold")
    table.add_column("Service", style="cyan")
    table.add_column("Modules")
    table.add_column("API Endpoints")
    table.add_column("Status", style="green")

    for sg in arch["serviceGroups"]:
        endpoints = [
            e for contract in arch["apiContracts"]
            if contract["service"] == sg["name"]
            for e in contract["endpoints"]
        ]
        table.add_row(
            sg["name"],
            ", ".join(sg["modules"]),
            str(len(endpoints)),
            "LOCKED",
        )

    console.print(table)
    console.print()
    console.print("[dim]Both semantic and architecture mappings are now locked.[/dim]")
    console.print(f"[dim]Next step: modernize generate <service-group>[/dim]")
