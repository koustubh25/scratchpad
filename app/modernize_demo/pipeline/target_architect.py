"""Target architecture derivation, review, and locking."""

from __future__ import annotations

from pathlib import Path
import re

from ..adapters.target.python_backend import conventions as python_conventions
from ..adapters.target.react_frontend import conventions as react_conventions
from ..core.audit import log_event, now_iso
from ..core.hashing import sha256_json
from ..core.invalidation import current_discovery_fingerprint
from ..core.rendering import render_template
from ..core.state import ProjectState

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def choose_target_stack(
    state: ProjectState,
    stack_entries: list[dict[str, str]],
    *,
    architecture_style: str,
    deployment_style: str,
) -> dict:
    """Persist the selected target stack after source architecture lock."""
    if state.get_step_status("lock_source_architecture") != "completed":
        raise RuntimeError("source architecture lock is required before choosing target stack")
    if not stack_entries:
        raise RuntimeError("at least one target stack entry is required")

    payload = {
        "selectedAt": now_iso(),
        "selectedStack": stack_entries,
        "architectureStyle": architecture_style,
        "deploymentStyle": deployment_style,
    }
    state.write_json("architecture", "target-stack.json", payload)

    state.update_project_config(
        target_stack=stack_entries,
        target_architecture_profile={
            "architectureStyle": architecture_style,
            "deploymentStyle": deployment_style,
        },
    )

    state.update_step(
        "choose_target_stack",
        "completed",
        targetStack=stack_entries,
        architectureStyle=architecture_style,
        deploymentStyle=deployment_style,
    )
    log_event(
        state,
        "target-stack.selected",
        targetStack=stack_entries,
        architectureStyle=architecture_style,
        deploymentStyle=deployment_style,
    )
    return payload


def run_target_architect(state: ProjectState) -> dict:
    """Derive the Python + React target architecture from locked inputs."""
    if state.get_step_status("lock_source_architecture") != "completed":
        raise RuntimeError("source architecture lock is required before target architecture")
    if state.get_step_status("choose_target_stack") != "completed":
        raise RuntimeError("target stack must be chosen before target architecture")

    source_architecture = state.read_json("architecture", "source-architecture.json")
    target_stack = state.read_json("architecture", "target-stack.json")
    slice_manifest = state.read_json("discovery", "demo-slice.json")
    if not slice_manifest:
        raise RuntimeError("discover must run before target architecture")

    modules = slice_manifest.get("selectedModules", [])
    semantics = sorted(
        [state.read_json("semantics", f"{module}.semantic.json") for module in modules],
        key=lambda item: item["module"].lower(),
    )
    facts_by_module = {module: state.read_json("facts", f"{module}.facts.json") for module in modules}
    source_modules = {module["module"]: module for module in source_architecture.get("modules", [])}

    services = []
    endpoints = []
    ui_components = []
    mappings = []
    data_ownership: dict[str, set[str]] = {}
    seen_services = set()
    seen_endpoints = set()
    seen_ui_components = set()
    seen_mappings = set()
    for semantic in semantics:
        module = semantic["module"]
        facts = facts_by_module.get(module, {})
        source_module = source_modules.get(module, {})
        role = _normalize_target_role(semantic, facts, source_module)
        if role == "request-entrypoint":
            component_name = _ui_component_name(module, semantic)
            ui_evidence = facts.get("ui_evidence", {})
            _append_unique(
                ui_components,
                seen_ui_components,
                (component_name, module),
                {
                    "name": component_name,
                    "kind": "page",
                    "owns": _ui_component_ownership(facts),
                    "mapsFrom": module,
                    "title": ui_evidence.get("title") or component_name,
                    "headings": ui_evidence.get("headings", []),
                    "forms": ui_evidence.get("forms", []),
                    "links": ui_evidence.get("links", []),
                    "redirects": ui_evidence.get("redirects", []),
                    "stylesheets": ui_evidence.get("stylesheets", []),
                    "errorRegions": ui_evidence.get("errorRegions", []),
                    "endpoints": [entry.get("path") for entry in facts.get("endpoints", []) if entry.get("path")],
                },
            )
            _append_unique(
                mappings,
                seen_mappings,
                (module, component_name, "ui-flow"),
                {"source": module, "target": component_name, "kind": "ui-flow"},
            )
            for endpoint in _infer_ui_api_contracts(module, semantic, facts, semantics):
                _append_unique(
                    endpoints,
                    seen_endpoints,
                    (endpoint["service"], endpoint["method"], endpoint["path"], endpoint["source"]),
                    endpoint,
                )
            continue

        service_name = _service_name_for(module, semantic, source_module)
        if service_name not in seen_services:
            services.append(
                {
                    "name": service_name,
                    "runtime": "python-backend",
                    "responsibility": semantic["summary"],
                }
            )
            seen_services.add(service_name)

        _append_unique(
            mappings,
            seen_mappings,
            (module, service_name, "service"),
            {"source": module, "target": service_name, "kind": "service"},
        )
        data_ownership.setdefault(service_name, set()).update(source_module.get("tables", []))

        for endpoint in _infer_service_contracts(service_name, module, semantic, facts):
            _append_unique(
                endpoints,
                seen_endpoints,
                (endpoint["service"], endpoint["method"], endpoint["path"], endpoint["source"]),
                endpoint,
            )

    architecture = {
        "artifactType": "target-architecture",
        "version": "1.0",
        "targetStack": target_stack["selectedStack"],
        "targetProfile": {
            "architectureStyle": target_stack.get("architectureStyle", "service-oriented"),
            "deploymentStyle": target_stack.get("deploymentStyle", "single-deployable"),
        },
        "services": services,
        "uiComponents": ui_components,
        "apiContracts": endpoints,
        "sourceMappings": mappings,
        "dataOwnership": [
            {"service": service, "owns": sorted(tables)} for service, tables in sorted(data_ownership.items())
        ],
        "generationBoundaries": {
            "generated": ["backend routes", "backend service layer", "frontend pages", "static assets"],
            "manual": [
                "legacy-side cutover hooks",
                "production reverse proxy changes",
                "database schema migration",
                "data migration and backfill",
            ],
        },
        "sourceArchitectureSummary": source_architecture["summary"],
    }
    adapter_conventions = {
        "backend": python_conventions(),
        "frontend": react_conventions(),
    }
    state.write_json("architecture", "target-architecture.json", architecture)
    state.write_json("architecture", "target-adapter-conventions.json", adapter_conventions)
    _write_target_review_state(state)
    markdown = render_template(
        TEMPLATE_DIR,
        "target_architecture.md.j2",
        architecture=architecture,
        conventions=adapter_conventions,
        target_stack_label=", ".join(
            f"`{item['adapter']}` ({item['role']})" for item in architecture["targetStack"]
        ),
    )
    state.write_text("architecture", "target-architecture.md", markdown)
    state.update_step("target_architect", "completed", services=len(services))
    state.update_step("review_target_architecture", "pending")
    log_event(state, "stage.completed", stage="target_architect", services=len(services))
    return architecture


def _normalize_target_role(semantic: dict, facts: dict, source_module: dict) -> str:
    """Map provider-specific role wording back to canonical internal roles."""
    module = (semantic.get("module") or "").strip().lower()
    role = (semantic.get("module_role") or "").strip().lower()
    summary = (semantic.get("summary") or "").strip().lower()
    capabilities = " ".join(
        (capability.get("description") or "") for capability in semantic.get("business_capabilities", [])
    ).lower()
    ui_evidence = facts.get("ui_evidence", {}) if facts else {}
    combined = " ".join(part for part in [module, role, summary, capabilities] if part)

    if (
        facts.get("module_type") == "template"
        or source_module.get("endpoints")
        or ui_evidence.get("forms")
        or ui_evidence.get("headings")
        or ui_evidence.get("title")
        or ui_evidence.get("links")
    ):
        return "request-entrypoint"

    if any(
        token in combined
        for token in ["request-entrypoint", "entrypoint", "handler", "render the login form", "authentication ui", "user interface", "login page"]
    ):
        return "request-entrypoint"
    if any(
        token in combined
        for token in [
            "identity-service",
            "auth-service",
            "authentication",
            "user management",
            "user management service",
            "identity checks",
        ]
    ):
        return "identity-service"
    if any(
        token in combined
        for token in ["order-service", "orderservice", "order management", "customer orders", "order lifecycle", "canceling customer orders"]
    ):
        return "order-service"
    return role or "application-service"


def _service_name_for(module: str, semantic: dict, source_module: dict) -> str:
    role = (semantic.get("module_role") or source_module.get("role") or "").strip().lower()
    if any(token in role for token in ["identity-service", "authentication", "user management"]):
        return "auth-service"
    if "order" in role:
        return "orders-service"
    module_base = _module_base_name(module)
    return f"{module_base}-service" if module_base else f"{_slugify(module)}-service"


def _ui_component_name(module: str, semantic: dict) -> str:
    role = (semantic.get("module_role") or "").strip().lower()
    if "login" in role or "authentication" in role or "sign-in" in (semantic.get("summary") or "").lower():
        return "LoginPage"
    return f"{_titleize(module)}Page"


def _ui_component_ownership(facts: dict) -> str:
    forms = facts.get("ui_evidence", {}).get("forms", [])
    if not forms:
        return "page state"
    names = [item.get("name") for form in forms for item in form.get("inputs", []) if item.get("name")]
    return f"{', '.join(names)} form state" if names else "page state"


def _infer_ui_api_contracts(module: str, semantic: dict, facts: dict, semantics: list[dict]) -> list[dict]:
    dependencies = {dependency.lower(): dependency for dependency in facts.get("dependencies", [])}
    backend_targets = [
        item for item in semantics if item["module"].lower() in dependencies
    ]
    endpoints = []
    path = _primary_ui_path(facts)
    source = f"{module}.{facts.get('functions', [{}])[0].get('name', 'render')}"
    if backend_targets:
        for target in backend_targets:
            service_name = _service_name_for(target["module"], target, {})
            endpoints.append(
                {
                    "service": service_name,
                    "path": path,
                    "method": "POST",
                    "source": source,
                }
            )
    elif path:
        endpoints.append(
            {
                "service": "web-entry",
                "path": path,
                "method": "POST",
                "source": source,
            }
        )
    return endpoints


def _primary_ui_path(facts: dict) -> str:
    endpoints = [entry["path"] for entry in facts.get("endpoints", []) if entry["path"].endswith(".cfm") is False]
    if endpoints:
        return endpoints[0]
    template_paths = [entry["path"] for entry in facts.get("endpoints", [])]
    return template_paths[0] if template_paths else f"/{_slugify(facts.get('module', 'page'))}"


def _infer_service_contracts(service_name: str, module: str, semantic: dict, facts: dict) -> list[dict]:
    contracts = []
    base_resource = _resource_name(module, semantic, facts)
    for capability in semantic.get("business_capabilities", []):
        function_name = capability["function"]
        method, path = _contract_for_function(base_resource, function_name)
        contracts.append(
            {
                "service": service_name,
                "path": path,
                "method": method,
                "source": f"{module}.{function_name}",
            }
        )
    return contracts


def _resource_name(module: str, semantic: dict, facts: dict) -> str:
    module_base = _module_base_name(module)
    tables = sorted(set(facts.get("reads", []) + facts.get("writes", [])))
    preferred_tables = [table for table in tables if not table.endswith("_items")] or tables
    if module_base:
        for table in preferred_tables:
            singular = table[:-1] if table.endswith("s") else table
            if module_base in {table, singular} or module_base in singular or singular in module_base:
                return _slugify(singular)
    if preferred_tables:
        return _slugify(preferred_tables[0].rstrip("s"))
    return module_base or _slugify(module.replace("Service", ""))


def _contract_for_function(resource: str, function_name: str) -> tuple[str, str]:
    lower = function_name.lower()
    base = f"/api/{resource}s"
    if lower.startswith(("get", "list", "fetch", "find")):
        return "GET", base
    if lower.startswith(("create", "add", "submit")):
        return "POST", base
    if lower.startswith(("update", "edit")):
        return "PUT", base
    if lower.startswith(("delete", "remove")):
        return "DELETE", base
    if lower.startswith(("cancel", "approve", "reject")):
        return "POST", f"{base}/{_action_suffix(function_name)}"
    if lower.startswith(("authenticate", "login", "sign")):
        return "POST", f"/api/{resource}/authenticate"
    return "POST", f"{base}/{_slugify(lower)}"


def _action_suffix(function_name: str) -> str:
    """Derive a cleaner action suffix from a verb-led function name."""
    words = _split_identifier_words(function_name)
    if not words:
        return _slugify(function_name)
    primary = words[0]
    remainder = words[1:]
    if not remainder:
        return primary
    if remainder[0] in {"order", "orders", "user", "users", "item", "items", "profile"}:
        return primary
    return "-".join([primary, *remainder])


def _slugify(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "-" for char in value.strip().lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def _titleize(value: str) -> str:
    parts = [part for part in _slugify(value).split("-") if part]
    return "".join(part.capitalize() for part in parts) or "Module"


def _module_base_name(module: str) -> str:
    base = module
    for suffix in ("Service", "Page", ".cfm", ".cfc"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return _slugify(base)


def _split_identifier_words(value: str) -> list[str]:
    """Split camelCase/PascalCase/snake_case names into lower-case words."""
    normalized = value.replace("_", " ").replace("-", " ")
    spaced = []
    for token in normalized.split():
        pieces = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\\d+", token)
        spaced.extend(piece.lower() for piece in pieces if piece)
    return spaced or [_slugify(value)]


def _append_unique(items: list[dict], seen: set[tuple], key: tuple, value: dict) -> None:
    """Append a value once for a stable deduplicated target architecture."""
    if key in seen:
        return
    items.append(value)
    seen.add(key)


def review_target_architecture(state: ProjectState) -> dict:
    """Return target architecture review state."""
    review_state = state.read_json("architecture", "target-architecture-review.json")
    if not review_state:
        raise RuntimeError("target architecture has not been derived yet")
    return review_state


def approve_target_architecture(state: ProjectState, reviewer: str = "demo-reviewer") -> dict:
    """Approve the derived target architecture."""
    review_state = review_target_architecture(state)
    review_state.update(
        {
            "status": "approved",
            "approved": True,
            "approvedBy": reviewer,
            "approvedAt": now_iso(),
        }
    )
    state.write_json("architecture", "target-architecture-review.json", review_state)
    state.update_step("review_target_architecture", "completed")
    log_event(state, "architecture.approved", kind="target", reviewer=reviewer)
    return review_state


def lock_target_architecture(state: ProjectState, reviewer: str = "demo-reviewer") -> dict:
    """Lock the approved target architecture."""
    review_state = review_target_architecture(state)
    if not review_state.get("approved"):
        raise RuntimeError("target architecture must be approved before lock")

    architecture = state.read_json("architecture", "target-architecture.json")
    conventions = state.read_json("architecture", "target-adapter-conventions.json")
    lock = {
        "lockType": "target-architecture",
        "version": "1.0",
        "lockedAt": now_iso(),
        "lockedBy": reviewer,
        "sourceDiscoveryFingerprint": current_discovery_fingerprint(state),
        "artifactFingerprints": {
            "architecture/target-architecture.json": sha256_json(architecture),
            "architecture/target-adapter-conventions.json": sha256_json(conventions),
        },
        "reviewState": review_state,
    }
    state.write_json("locked", "target-architecture-lock.json", lock)
    manifest = state.read_json("locked", "lock-manifest.json") or {}
    manifest["targetArchitectureLock"] = {"lockedAt": lock["lockedAt"], "reviewer": reviewer}
    state.write_json("locked", "lock-manifest.json", manifest)
    state.update_step("lock_target_architecture", "completed")
    log_event(state, "lock.created", lockType="target-architecture", reviewer=reviewer)
    return lock


def _write_target_review_state(state: ProjectState) -> None:
    state.write_json(
        "architecture",
        "target-architecture-review.json",
        {
            "status": "pending",
            "approved": False,
            "approvedBy": None,
            "approvedAt": None,
            "notes": [],
        },
    )
