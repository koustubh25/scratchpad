"""AST generation stage."""

from __future__ import annotations

from pathlib import Path

from ..adapters.source.coldfusion import parse_file
from ..core.audit import log_event
from ..core.models import to_dict
from ..core.state import ProjectState


def run_parse(state: ProjectState) -> list[dict]:
    """Parse the current demo slice into AST artifacts."""
    slice_manifest = state.read_json("discovery", "demo-slice.json")
    if not slice_manifest:
        raise RuntimeError("discover must run before parse")

    selected_modules = set(slice_manifest.get("selectedModules", []))
    for path in state.list_files("ast", ".ast.json"):
        if path.stem.replace(".ast", "") not in selected_modules:
            path.unlink(missing_ok=True)

    parsed = []
    for file_path in slice_manifest["selectedFiles"]:
        ast = parse_file(Path(file_path))
        parsed.append(to_dict(ast))
        state.write_json("ast", f"{ast.module}.ast.json", ast)

    state.update_step("parse", "completed", modulesParsed=len(parsed))
    log_event(state, "stage.completed", stage="parse", modules=len(parsed))
    return parsed
