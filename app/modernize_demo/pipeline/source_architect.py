"""Source architecture derivation, review, and locking."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re

from ..core.audit import log_event, now_iso
from ..core.hashing import sha256_json
from ..core.invalidation import current_discovery_fingerprint
from ..core.rendering import render_template
from ..core.state import ProjectState


def run_source_architect(state: ProjectState) -> dict:
    """Derive a graph-shaped source architecture artifact and render its document."""
    if state.get_step_status("lock_semantics") != "completed":
        raise RuntimeError("semantic lock is required before source architecture")

    slice_manifest = state.read_json("discovery", "demo-slice.json")
    if not slice_manifest:
        raise RuntimeError("discover must run before source architecture")

    modules = slice_manifest.get("selectedModules", [])
    semantics = [state.read_json("semantics", f"{module}.semantic.json") for module in modules]
    facts = {module: state.read_json("facts", f"{module}.facts.json") for module in modules}

    nodes = []
    edges = []
    clusters = []
    hotspot_scores = defaultdict(int)
    seen_nodes = set()
    seen_edges = set()
    module_summaries = []
    state_dependencies = []
    config_dependencies = []
    external_integrations = []
    dependency_graph = []

    modules_by_role = defaultdict(list)
    module_name_lookup = {semantic["module"].strip().lower(): semantic["module"] for semantic in semantics}
    known_endpoint_paths = set()
    for fact in facts.values():
        known_endpoint_paths.update(endpoint["path"] for endpoint in fact["endpoints"])

    for semantic in semantics:
        module = semantic["module"]
        facts_for_module = facts[module]
        normalized_role = _normalize_source_role(semantic["module_role"], module, semantic["summary"])
        _append_node(seen_nodes, nodes, {"id": module, "type": "module", "label": module, "role": normalized_role})
        modules_by_role[normalized_role].append(module)

        normalized_dependencies = [
            _normalize_dependency_target(dependency, module_name_lookup)
            for dependency in facts_for_module["dependencies"]
            if dependency not in known_endpoint_paths
        ]
        module_summaries.append(
            {
                "module": module,
                "role": normalized_role,
                "summary": semantic["summary"],
                "dependencies": sorted(set(normalized_dependencies)),
                "configUsage": sorted(set(facts_for_module["config_usage"])),
                "sessionUsage": sorted(set(facts_for_module["session_usage"])),
                "endpoints": sorted({endpoint["path"] for endpoint in facts_for_module["endpoints"]}),
                "tables": sorted({entry["table"] for entry in facts_for_module["tables_touched"]}),
            }
        )

        seen_dependency_graph = set()

        for touched in facts_for_module["tables_touched"]:
            table = touched["table"]
            table_id = f"table:{table}"
            _append_node(seen_nodes, nodes, {"id": table_id, "type": "table", "label": table})
            op = "reads" if touched["operation"] == "SELECT" else "writes"
            _append_edge(seen_edges, edges, {"from": module, "to": table_id, "type": op})
            dep_key = (module, table, op)
            if dep_key not in seen_dependency_graph:
                dependency_graph.append({"from": module, "to": table, "kind": op})
                seen_dependency_graph.add(dep_key)
            hotspot_scores[module] += 1

        for dependency in facts_for_module["dependencies"]:
            if dependency in known_endpoint_paths:
                continue

            target = _normalize_dependency_target(dependency, module_name_lookup)
            target_type = "module" if target in module_name_lookup.values() else "external_or_unknown"
            _append_node(seen_nodes, nodes, {"id": target, "type": target_type, "label": target})
            _append_edge(seen_edges, edges, {"from": module, "to": target, "type": "depends_on"})
            dep_key = (module, target, "depends_on")
            if dep_key not in seen_dependency_graph:
                dependency_graph.append({"from": module, "to": target, "kind": "depends_on"})
                seen_dependency_graph.add(dep_key)
            if target_type == "external_or_unknown":
                external_integrations.append({"module": module, "dependency": target})
            hotspot_scores[module] += 1

        for state_key in facts_for_module["session_usage"]:
            state_id = f"state:{state_key}"
            _append_node(seen_nodes, nodes, {"id": state_id, "type": "state", "label": state_key})
            _append_edge(seen_edges, edges, {"from": module, "to": state_id, "type": "writes_state"})
            state_dependencies.append({"module": module, "state": state_key, "access": "write"})

        for endpoint in facts_for_module["endpoints"]:
            endpoint_id = f"endpoint:{endpoint['path']}"
            _append_node(seen_nodes, nodes, {"id": endpoint_id, "type": "endpoint", "label": endpoint["path"]})
            _append_edge(seen_edges, edges, {"from": endpoint_id, "to": module, "type": "routes_to"})

        for config_key in facts_for_module["config_usage"]:
            config_dependencies.append({"module": module, "config": config_key})

    for role, members in modules_by_role.items():
        clusters.append({"id": _slugify(role), "members": sorted(members), "description": role})

    architecture = {
        "artifactType": "source-architecture",
        "version": "1.0",
        "nodes": nodes,
        "edges": edges,
        "mermaid": _build_mermaid_graph(nodes, edges, external_integrations),
        "clusters": clusters,
        "modules": sorted(module_summaries, key=lambda item: item["module"].lower()),
        "stateDependencies": sorted(state_dependencies, key=lambda item: (item["module"], item["state"])),
        "configDependencies": sorted(config_dependencies, key=lambda item: (item["module"], item["config"])),
        "externalIntegrations": sorted(external_integrations, key=lambda item: (item["module"], item["dependency"])),
        "dependencyGraph": sorted(dependency_graph, key=lambda item: (item["from"], item["to"], item["kind"])),
        "hotspots": sorted(
            [{"node": node, "score": score} for node, score in hotspot_scores.items()],
            key=lambda item: (-item["score"], item["node"]),
        ),
        "summary": {
            "moduleCount": len([node for node in nodes if node["type"] == "module"]),
            "tableCount": len([node for node in nodes if node["type"] == "table"]),
            "endpointCount": len([node for node in nodes if node["type"] == "endpoint"]),
        },
    }
    state.write_json("architecture", "source-architecture.json", architecture)
    _write_source_review_state(state)
    markdown = render_template(
        TEMPLATE_DIR,
        "source_architecture.md.j2",
        architecture=architecture,
    )
    state.write_text("architecture", "source-architecture.md", markdown)
    render_source_architecture_review_documents(state)
    state.update_step("source_architect", "completed", modules=architecture["summary"]["moduleCount"])
    state.update_step("review_source_architecture", "pending")
    log_event(state, "stage.completed", stage="source_architect", modules=architecture["summary"]["moduleCount"])
    return architecture


def review_source_architecture(state: ProjectState) -> dict:
    """Return source architecture review state."""
    review_state = _load_source_review_state(state)
    architecture = state.read_json("architecture", "source-architecture.json")
    if not architecture:
        raise RuntimeError("source architecture has not been derived yet")
    render_source_architecture_review_documents(state)

    module_entries = [
        {
            "module": module["module"],
            "role": module["role"],
            "reviewDocument": str(state.path_for("docs", f"source-architecture/modules/{module['module']}.md")),
        }
        for module in architecture["modules"]
    ]
    return {
        "status": review_state["status"],
        "indexDocument": str(state.path_for("docs", "source-architecture/index.md")),
        "summaryDocument": str(state.path_for("architecture", "source-architecture.md")),
        "modules": module_entries,
    }


def approve_source_architecture(state: ProjectState, reviewer: str = "demo-reviewer") -> dict:
    """Approve the derived source architecture."""
    review_state = _load_source_review_state(state)
    review_state.update(
        {
            "status": "approved",
            "approved": True,
            "approvedBy": reviewer,
            "approvedAt": now_iso(),
        }
    )
    state.write_json("architecture", "source-architecture-review.json", review_state)
    render_source_architecture_review_documents(state)
    state.update_step("review_source_architecture", "completed")
    log_event(state, "architecture.approved", kind="source", reviewer=reviewer)
    return review_state


def lock_source_architecture(state: ProjectState, reviewer: str = "demo-reviewer") -> dict:
    """Lock the source architecture after review."""
    review_state = _load_source_review_state(state)
    if not review_state.get("approved"):
        raise RuntimeError("source architecture must be approved before lock")

    architecture = state.read_json("architecture", "source-architecture.json")
    doc_hash = sha256_json(architecture)
    lock = {
        "lockType": "source-architecture",
        "version": "1.0",
        "lockedAt": now_iso(),
        "lockedBy": reviewer,
        "sourceDiscoveryFingerprint": current_discovery_fingerprint(state),
        "artifactFingerprints": {
            "architecture/source-architecture.json": doc_hash,
        },
        "reviewState": review_state,
    }
    state.write_json("locked", "source-architecture-lock.json", lock)
    manifest = state.read_json("locked", "lock-manifest.json") or {}
    manifest["sourceArchitectureLock"] = {"lockedAt": lock["lockedAt"], "reviewer": reviewer}
    state.write_json("locked", "lock-manifest.json", manifest)
    state.update_step("lock_source_architecture", "completed")
    log_event(state, "lock.created", lockType="source-architecture", reviewer=reviewer)
    return lock


def _write_source_review_state(state: ProjectState) -> None:
    review_state = {
        "status": "pending",
        "approved": False,
        "approvedBy": None,
        "approvedAt": None,
        "notes": [],
    }
    state.write_json("architecture", "source-architecture-review.json", review_state)


def _load_source_review_state(state: ProjectState) -> dict:
    review_state = state.read_json("architecture", "source-architecture-review.json")
    if not review_state:
        raise RuntimeError("source architecture has not been derived yet")
    return review_state


def render_source_architecture_review_documents(state: ProjectState) -> dict:
    """Render review-friendly source architecture docs: index plus one module doc per module."""
    architecture = state.read_json("architecture", "source-architecture.json")
    review_state = state.read_json("architecture", "source-architecture-review.json")
    if not architecture or not review_state:
        raise RuntimeError("source architecture has not been derived yet")

    modules = sorted(architecture["modules"], key=lambda item: item["module"].lower())
    clusters_by_member = {}
    for cluster in architecture["clusters"]:
        for member in cluster["members"]:
            clusters_by_member[member] = cluster["description"]

    module_entries = []
    for module in modules:
        dependency_edges = [
            edge for edge in architecture["dependencyGraph"] if edge["from"] == module["module"]
        ]
        facts = state.read_json("facts", f"{module['module']}.facts.json") or {}
        module_doc_path = state.write_text(
            "docs",
            f"source-architecture/modules/{module['module']}.md",
            render_template(
                TEMPLATE_DIR,
                "source_architecture_module.md.j2",
                module=module,
                facts=facts,
                subsystem=clusters_by_member.get(module["module"], module["role"]),
                dependency_edges=dependency_edges,
            ),
        )
        module_entries.append(
            {
                "module": module["module"],
                "role": module["role"],
                "subsystem": clusters_by_member.get(module["module"], module["role"]),
                "tables": module["tables"],
                "endpoints": module["endpoints"],
                "dependencies": module["dependencies"],
                "reviewDocument": str(module_doc_path),
            }
        )

    index_doc_path = state.write_text(
        "docs",
        "source-architecture/index.md",
        render_template(
            TEMPLATE_DIR,
            "source_architecture_index.md.j2",
            architecture=architecture,
            review_status=review_state["status"],
            summary_document=str(state.path_for("architecture", "source-architecture.md")),
            modules=module_entries,
        ),
    )
    return {
        "indexDocument": str(index_doc_path),
        "modules": module_entries,
    }
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def _build_mermaid_graph(nodes: list[dict], edges: list[dict], external_integrations: list[dict]) -> dict:
    node_ids = {node["id"]: f"n{index}" for index, node in enumerate(nodes, start=1)}
    diagram_edges = [
        {
            "fromId": node_ids[edge["from"]],
            "toId": node_ids[edge["to"]],
            "fromLabel": _mermaid_label(edge["from"]),
            "toLabel": _mermaid_label(edge["to"]),
            "label": _mermaid_label(edge["type"]),
        }
        for edge in edges
        if edge["from"] in node_ids and edge["to"] in node_ids
    ]

    external_edges = []
    external_ids: dict[str, str] = {}
    next_external_index = 1
    for integration in external_integrations:
        dependency = integration["dependency"]
        if dependency not in external_ids:
            external_ids[dependency] = f"ext{next_external_index}"
            next_external_index += 1
        module_id = node_ids.get(integration["module"])
        if not module_id:
            continue
        external_edges.append(
            {
                "fromId": module_id,
                "toId": external_ids[dependency],
                "fromLabel": _mermaid_label(integration["module"]),
                "toLabel": _mermaid_label(dependency),
                "label": "depends_on",
            }
        )

    return {
        "dependencyEdges": diagram_edges,
        "externalEdges": external_edges,
    }


def _mermaid_label(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', "&quot;")
        .replace("\n", " ")
        .strip()
    )


def _append_node(seen_nodes: set[str], nodes: list[dict], node: dict) -> None:
    node_id = node["id"]
    if node_id in seen_nodes:
        return
    nodes.append(node)
    seen_nodes.add(node_id)


def _append_edge(seen_edges: set[tuple[str, str, str]], edges: list[dict], edge: dict) -> None:
    key = (edge["from"], edge["to"], edge["type"])
    if key in seen_edges:
        return
    edges.append(edge)
    seen_edges.add(key)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _normalize_source_role(role: str, module: str, summary: str = "") -> str:
    role_lower = (role or "").strip().lower()
    combined = " ".join(part for part in [role_lower, module.lower(), (summary or "").strip().lower()] if part)
    if "order" in combined:
        return "Order Management Service"
    if any(token in combined for token in ["user management", "identity", "authenticate", "user profile"]):
        return "User Management Service"
    if role_lower == "ui" or any(
        token in combined for token in ["request-entrypoint", "handler", "authentication ui", "user interface", "login page"]
    ):
        return "User Interface for Authentication"
    return role or module


def _normalize_dependency_target(dependency: str, module_name_lookup: dict[str, str]) -> str:
    normalized = dependency.strip()
    if not normalized:
        return dependency
    return module_name_lookup.get(normalized.lower(), normalized)
