"""Source and config discovery stage."""

from __future__ import annotations

from pathlib import Path

from ..adapters.source.coldfusion import demo_slice_from_discovery, discover_source
from ..core.audit import log_event
from ..core.state import ProjectState


def run_discover(state: ProjectState) -> dict:
    """Discover source files, config inputs, and the demo slice."""
    migration = state.load_migration()
    source_root = Path(migration["project"]["source_path"])
    discovery = discover_source(source_root)
    slice_manifest = demo_slice_from_discovery(discovery)
    state.write_json("discovery", "source-discovery.json", discovery)
    state.write_json("discovery", "demo-slice.json", slice_manifest)
    state.update_step("discover", "completed", filesDiscovered=len(discovery["discoveredSourceFiles"]))
    log_event(state, "stage.completed", stage="discover", files=len(discovery["discoveredSourceFiles"]))
    return {"discovery": discovery, "demoSlice": slice_manifest}

