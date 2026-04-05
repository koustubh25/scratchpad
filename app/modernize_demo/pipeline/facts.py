"""Deterministic fact extraction stage."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from ..core.audit import log_event
from ..core.models import FactArtifact
from ..core.state import ProjectState


def run_facts(state: ProjectState) -> list[dict]:
    """Extract normalized facts from AST artifacts."""
    slice_manifest = state.read_json("discovery", "demo-slice.json")
    if not slice_manifest:
        raise RuntimeError("discover must run before facts")

    modules = slice_manifest.get("selectedModules", [])
    ast_files = [state.path_for("ast", f"{module}.ast.json") for module in modules]
    if not ast_files or any(not path.exists() for path in ast_files):
        raise RuntimeError("parse must run before facts")

    selected_modules = set(modules)
    for path in state.list_files("facts", ".facts.json"):
        if path.stem.replace(".facts", "") not in selected_modules:
            path.unlink(missing_ok=True)

    facts = []
    for ast_file in ast_files:
        ast = state.read_json("ast", ast_file.name)
        artifact = build_facts(ast)
        facts.append(artifact)
        state.write_json("facts", f"{artifact.module}.facts.json", artifact)

    state.update_step("facts", "completed", modules=len(facts))
    log_event(state, "stage.completed", stage="facts", modules=len(facts))
    return [state.read_json("facts", f"{item.module}.facts.json") for item in facts]


def build_facts(ast: dict) -> FactArtifact:
    """Build one fact artifact from one AST artifact."""
    reads: list[str] = []
    writes: list[str] = []
    tables = []
    session_usage = set()
    config_usage = set(ast.get("config_usage", []))
    calls = set()
    includes = set()
    endpoints = []
    dependencies = set()
    functions = []
    inference_notes = []

    for endpoint in ast.get("endpoints", []):
        endpoints.append({"path": endpoint, "source": "deterministic"})

    for function in ast.get("functions", []):
        function_tables = set()
        for query in function.get("queries", []):
            operation = query["operation"]
            for table in query["tables"]:
                function_tables.add(table)
                tables.append({"table": table, "operation": operation, "function": function["name"]})
                if operation == "SELECT":
                    reads.append(table)
                else:
                    writes.append(table)
        for scope_write in function.get("scope_writes", []):
            if scope_write.startswith("session."):
                session_usage.add(scope_write)
        function_calls = {call for call in function.get("calls", []) if not _is_route_like(call)}
        calls.update(function_calls)
        inferred_dependencies = {
            call.split(".")[0] for call in function_calls if "." in call and not call.startswith("session.")
        }
        dependencies.update(inferred_dependencies)
        functions.append(
            {
                "name": function["name"],
                "tables": sorted(function_tables),
                "throws": function.get("throws", []),
                "calls": sorted(function_calls),
                "scopeWrites": function.get("scope_writes", []),
                "conditionals": function.get("conditionals", []),
            }
        )

    if ast["module_type"] == "template":
        dependencies.update(call for call in calls if call[0].isupper() and "." not in call)
        if ast.get("endpoints"):
            inference_notes.append(
                {
                    "field": "endpoints",
                    "reason": "Endpoint paths for templates are inferred from filenames and cfform actions.",
                }
            )

    for dep in list(dependencies):
        if dep.lower().endswith(".cfm"):
            includes.add(dep)

    return FactArtifact(
        module=ast["module"],
        file_path=ast["source_file"],
        module_type=ast["module_type"],
        reads=sorted(set(reads)),
        writes=sorted(set(writes)),
        tables_touched=sorted(tables, key=lambda item: (item["table"], item["function"], item["operation"])),
        session_usage=sorted(session_usage),
        config_usage=sorted(config_usage),
        calls=sorted(calls),
        includes=sorted(includes),
        endpoints=endpoints,
        dependencies=sorted(dep for dep in dependencies if dep and dep != ast["module"] and not _is_route_like(dep)),
        functions=functions,
        inference_notes=inference_notes,
        ui_evidence=_normalize_ui_evidence(ast.get("ui_evidence", {})),
    )


def _is_route_like(value: str) -> bool:
    return value.startswith("/") or value.lower().endswith(".cfm")


def _normalize_ui_evidence(ui_evidence: dict) -> dict:
    """Return a stable copy of UI evidence so nested input metadata is preserved."""
    return deepcopy(ui_evidence)
