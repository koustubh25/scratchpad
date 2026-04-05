"""Generation of the runnable Python + React demo app."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..adapters.ai.base import GeneratedApplication
from ..adapters.ai.registry import load_provider
from ..core.audit import log_event, now_iso
from ..core.invalidation import lock_is_stale
from ..core.state import ProjectState


def run_generate(state: ProjectState, app_name: str) -> dict:
    """Generate a runnable demo app from locked source and target artifacts."""
    required_locks = [
        "semantic-lock.json",
        "source-architecture-lock.json",
        "target-architecture-lock.json",
    ]
    for lock_name in required_locks:
        stale, reason = lock_is_stale(state, lock_name)
        if stale:
            raise RuntimeError(f"{lock_name} is stale or missing: {reason}")

    target_arch = state.read_json("architecture", "target-architecture.json")
    source_arch = state.read_json("architecture", "source-architecture.json")
    slice_manifest = state.read_json("discovery", "demo-slice.json") or {}
    modules = slice_manifest.get("selectedModules", [])
    ast_by_module = {module: state.read_json("ast", f"{module}.ast.json") for module in modules}
    facts_by_module = {module: state.read_json("facts", f"{module}.facts.json") for module in modules}
    semantics_by_module = {module: state.read_json("semantics", f"{module}.semantic.json") for module in modules}
    service_root = state.path_for("services", app_name)
    if service_root.exists():
        shutil.rmtree(service_root)
    backend_root = service_root / "backend"
    frontend_root = service_root / "frontend"
    backend_root.mkdir(parents=True, exist_ok=True)
    frontend_root.mkdir(parents=True, exist_ok=True)

    behavior_catalog = _build_behavior_catalog(target_arch, source_arch, ast_by_module, facts_by_module, semantics_by_module)
    sample_data = _build_sample_data(target_arch, behavior_catalog)
    target_conventions = state.read_json("architecture", "target-adapter-conventions.json") or {}
    runtime_config = {
        "services": target_arch["services"],
        "uiComponents": target_arch["uiComponents"],
        "apiContracts": target_arch["apiContracts"],
        "sampleData": sample_data,
        "behaviorCatalog": behavior_catalog,
    }

    deterministic_generated_files = {
        "backend/app_logic.py": _app_logic_py(),
        "frontend/app.js": _frontend_app_js(),
        "frontend/styles.css": _frontend_styles_css(),
    }
    provider = load_provider(state)
    generation_context = _build_generation_context(
        app_name=app_name,
        target_arch=target_arch,
        source_arch=source_arch,
        target_conventions=target_conventions,
        slice_manifest=slice_manifest,
        ast_by_module=ast_by_module,
        facts_by_module=facts_by_module,
        semantics_by_module=semantics_by_module,
        behavior_catalog=behavior_catalog,
        runtime_config=runtime_config,
        deterministic_generated_files=deterministic_generated_files,
    )
    try:
        generated_application = provider.generate_application(generation_context)
        missing_files = {
            "backend/app_logic.py",
            "frontend/app.js",
            "frontend/styles.css",
        } - set(generated_application.files)
        if missing_files:
            raise RuntimeError(f"provider returned incomplete generation output: missing {sorted(missing_files)}")
    except Exception as exc:
        generated_application = GeneratedApplication(
            files=deterministic_generated_files,
            provider=f"{provider.name}:fallback",
            notes=[f"AI generation fell back to deterministic adapter output: {exc}"],
        )

    metadata = {
        "generatedAt": now_iso(),
        "appName": app_name,
        "generationProvider": generated_application.provider,
        "inputs": {
            "semanticLock": "locked/semantic-lock.json",
            "sourceArchitectureLock": "locked/source-architecture-lock.json",
            "targetArchitectureLock": "locked/target-architecture-lock.json",
        },
        "services": target_arch["services"],
        "uiComponents": target_arch["uiComponents"],
        "apiContracts": target_arch["apiContracts"],
        "behaviorCatalog": behavior_catalog,
        "generationNotes": generated_application.notes,
    }
    (service_root / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    (backend_root / "generated_config.json").write_text(json.dumps(runtime_config, indent=2, sort_keys=True), encoding="utf-8")

    app_logic = generated_application.files.get("backend/app_logic.py") or deterministic_generated_files["backend/app_logic.py"]
    frontend_app = generated_application.files.get("frontend/app.js") or deterministic_generated_files["frontend/app.js"]
    frontend_styles = generated_application.files.get("frontend/styles.css") or deterministic_generated_files["frontend/styles.css"]

    (backend_root / "app_logic.py").write_text(app_logic, encoding="utf-8")
    (backend_root / "server.py").write_text(_server_py(), encoding="utf-8")
    (backend_root / "README.md").write_text(_backend_readme(app_name), encoding="utf-8")

    (frontend_root / "index.html").write_text(_frontend_index_html(app_name), encoding="utf-8")
    (frontend_root / "styles.css").write_text(frontend_styles, encoding="utf-8")
    (frontend_root / "app.js").write_text(frontend_app, encoding="utf-8")

    state.update_step("generate", "completed", appName=app_name)
    log_event(state, "stage.completed", stage="generate", appName=app_name, provider=generated_application.provider)
    return {
        "appName": app_name,
        "outputRoot": str(service_root),
        "generatedFiles": sorted(
            str(path.relative_to(service_root))
            for path in service_root.rglob("*")
            if path.is_file()
        ),
    }


def _build_generation_context(
    *,
    app_name: str,
    target_arch: dict,
    source_arch: dict,
    target_conventions: dict,
    slice_manifest: dict,
    ast_by_module: dict[str, dict | None],
    facts_by_module: dict[str, dict | None],
    semantics_by_module: dict[str, dict | None],
    behavior_catalog: dict,
    runtime_config: dict,
    deterministic_generated_files: dict[str, str],
) -> dict:
    return {
        "appName": app_name,
        "targetArchitecture": target_arch,
        "sourceArchitecture": source_arch,
        "targetAdapterConventions": target_conventions,
        "demoSlice": slice_manifest,
        "astArtifacts": ast_by_module,
        "factArtifacts": facts_by_module,
        "semanticArtifacts": semantics_by_module,
        "behaviorCatalog": behavior_catalog,
        "runtimeConfig": runtime_config,
        "filesToGenerate": [
            "backend/app_logic.py",
            "frontend/app.js",
            "frontend/styles.css",
        ],
        "deterministicFallbackFiles": deterministic_generated_files,
    }


def _build_sample_data(target_arch: dict, behavior_catalog: dict) -> dict:
    resources = []
    for service in target_arch["services"]:
        resources.append(
            {
                "service": service["name"],
                "summary": service["responsibility"],
            }
        )
    return {
        "resources": resources,
        "authUsers": behavior_catalog.get("seedState", {}).get("authUsers", []),
        "products": behavior_catalog.get("seedState", {}).get("products", []),
        "orders": behavior_catalog.get("seedState", {}).get("orders", []),
    }


def _build_behavior_catalog(
    target_arch: dict,
    source_arch: dict | None,
    ast_by_module: dict[str, dict | None],
    facts_by_module: dict[str, dict | None],
    semantics_by_module: dict[str, dict | None],
) -> dict:
    service_lookup = {
        mapping["source"]: mapping["target"]
        for mapping in target_arch.get("sourceMappings", [])
        if mapping.get("kind") == "service"
    }
    module_summaries = {
        item["module"]: item
        for item in (source_arch or {}).get("modules", [])
    }

    modules = {}
    auth_users = []
    has_order_domain = False
    for module, ast in ast_by_module.items():
        if not ast:
            continue
        facts = facts_by_module.get(module) or {}
        semantic = semantics_by_module.get(module) or {}
        functions = {}
        for function in ast.get("functions", []):
            mode = _infer_function_mode(function, semantic, facts)
            functions[function["name"]] = {
                "mode": mode,
                "arguments": function.get("arguments", []),
                "queries": function.get("queries", []),
                "queryOperations": [query.get("operation", "").upper() for query in function.get("queries", [])],
                "conditionals": function.get("conditionals", []),
                "throws": function.get("throws", []),
                "scopeWrites": function.get("scope_writes", []),
                "calls": function.get("calls", []),
                "tables": sorted({table for query in function.get("queries", []) for table in query.get("tables", [])}),
                "returnType": function.get("return_type"),
            }
            if mode == "authenticate" and not auth_users:
                auth_users = _default_auth_users(function)
            if {"orders", "order_items", "products"} & set(functions[function["name"]]["tables"]):
                has_order_domain = True
        modules[module] = {
            "moduleType": ast.get("module_type"),
            "summary": semantic.get("summary") or module_summaries.get(module, {}).get("summary", ""),
            "role": semantic.get("module_role") or module_summaries.get(module, {}).get("role", ""),
            "dependencies": facts.get("dependencies", []),
            "tables": sorted(set(facts.get("reads", []) + facts.get("writes", []))),
            "sessionUsage": facts.get("session_usage", []),
            "configUsage": facts.get("config_usage", []),
            "uiEvidence": facts.get("ui_evidence", {}),
            "functions": functions,
            "service": service_lookup.get(module),
        }

    contracts = {}
    for contract in target_arch.get("apiContracts", []):
        source_ref = contract.get("source", "")
        module, _, function_name = source_ref.partition(".")
        function_behavior = (modules.get(module, {}).get("functions", {}) or {}).get(function_name, {})
        contract_key = f"{contract['method']} {contract['path']}"
        contract_behavior = {
            "sourceModule": module,
            "sourceFunction": function_name,
            "mode": function_behavior.get("mode", "generic"),
            "arguments": function_behavior.get("arguments", []),
            "throws": function_behavior.get("throws", []),
            "tables": function_behavior.get("tables", modules.get(module, {}).get("tables", [])),
            "sessionWrites": function_behavior.get("scopeWrites", []),
            "service": contract.get("service"),
        }
        if modules.get(module, {}).get("moduleType") == "template":
            delegated_auth = _find_delegated_auth_target(modules, module)
            if delegated_auth:
                contract_behavior.update(
                    {
                        "mode": "delegated-auth",
                        "delegateModule": delegated_auth["module"],
                        "delegateFunction": delegated_auth["function"],
                        "redirect": _primary_redirect(modules.get(module, {}).get("uiEvidence", {})),
                        "errorMessages": {
                            "InvalidCredentials": "Invalid email or password.",
                            "AccountLocked": "Your account has been locked. Please try again in 30 minutes.",
                        },
                    }
                )
        contracts[contract_key] = contract_behavior

    return {
        "modules": modules,
        "contracts": contracts,
        "seedState": {
            "authUsers": auth_users,
            "products": _default_products() if has_order_domain else [],
            "orders": _default_orders() if has_order_domain else [],
            "nextOrderId": 2002 if has_order_domain else 1000,
        },
    }


def _infer_function_mode(function: dict, semantic: dict, facts: dict) -> str:
    name = (function.get("name") or "").lower()
    throws = {value.lower() for value in function.get("throws", [])}
    arguments = {arg.get("name", "").lower() for arg in function.get("arguments", [])}
    queries = function.get("queries", [])
    ops = {query.get("operation", "").upper() for query in queries}

    if {"email", "password"}.issubset(arguments) and ("invalidcredentials" in throws or "accountlocked" in throws or "authenticate" in name):
        return "authenticate"
    if name.startswith(("get", "list", "fetch", "find")) or ops == {"SELECT"}:
        return "read"
    if name.startswith(("create", "add", "submit")) or "INSERT" in ops:
        return "create"
    if name.startswith(("update", "edit")) or "UPDATE" in ops:
        return "update"
    if name.startswith(("delete", "remove")) or "DELETE" in ops:
        return "delete"
    if name.startswith(("cancel", "approve", "reject")):
        return "action"
    return "generic"


def _default_auth_users(function: dict) -> list[dict]:
    session_writes = function.get("scope_writes", [])
    return [
        {
            "email": "demo@example.com",
            "password": "password123",
            "id": 101,
            "role": "user",
            "locked": False,
            "session": {key.split(".")[-1]: _default_session_value(key, 101, "user", "demo@example.com") for key in session_writes},
        },
        {
            "email": "locked@example.com",
            "password": "password123",
            "id": 102,
            "role": "user",
            "locked": True,
            "session": {key.split(".")[-1]: _default_session_value(key, 102, "user", "locked@example.com") for key in session_writes},
        },
    ]


def _default_session_value(scope_key: str, user_id: int, role: str, email: str):
    lower = scope_key.lower()
    if lower.endswith("userid"):
        return user_id
    if lower.endswith("userrole"):
        return role
    if lower.endswith("useremail"):
        return email
    return True


def _default_products() -> list[dict]:
    return [
        {"id": 1, "name": "Starter Kit", "price": 149.0, "stock_quantity": 12},
        {"id": 2, "name": "Team License", "price": 399.0, "stock_quantity": 8},
        {"id": 3, "name": "Support Pack", "price": 99.0, "stock_quantity": 20},
    ]


def _default_orders() -> list[dict]:
    return [
        {
            "id": 2001,
            "user_id": 101,
            "status": "pending",
            "total": 149.0,
            "created_at": "2026-04-05T00:00:00Z",
            "items": [
                {
                    "product_id": 1,
                    "quantity": 1,
                    "unit_price": 149.0,
                }
            ],
        }
    ]


def _find_delegated_auth_target(modules: dict[str, dict], template_module: str) -> dict | None:
    template = modules.get(template_module, {})
    for dependency in template.get("dependencies", []):
        functions = modules.get(dependency, {}).get("functions", {})
        for function_name, behavior in functions.items():
            if behavior.get("mode") == "authenticate":
                return {"module": dependency, "function": function_name}
    return None


def _primary_redirect(ui_evidence: dict) -> str | None:
    redirects = ui_evidence.get("redirects", []) if ui_evidence else []
    return redirects[0] if redirects else None


def _app_logic_py() -> str:
    return """from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path


CONFIG = json.loads((Path(__file__).resolve().parent / "generated_config.json").read_text(encoding="utf-8"))
API_CONTRACTS = CONFIG["apiContracts"]
SERVICES = CONFIG["services"]
UI_COMPONENTS = CONFIG["uiComponents"]
SAMPLE_DATA = CONFIG["sampleData"]
BEHAVIOR_CATALOG = CONFIG.get("behaviorCatalog", {})
SEED_STATE = BEHAVIOR_CATALOG.get("seedState", {})


def _initial_runtime_state() -> dict:
    auth_users = copy.deepcopy(SEED_STATE.get("authUsers", SAMPLE_DATA.get("authUsers", [])))
    products = copy.deepcopy(SEED_STATE.get("products", SAMPLE_DATA.get("products", [])))
    orders = copy.deepcopy(SEED_STATE.get("orders", SAMPLE_DATA.get("orders", [])))
    return {
        "failedAttempts": {},
        "authUsers": auth_users,
        "products": products,
        "orders": orders,
        "nextOrderId": SEED_STATE.get("nextOrderId", 1000),
    }


RUNTIME_STATE = _initial_runtime_state()


def list_contracts() -> list[dict]:
    return API_CONTRACTS


def get_runtime_summary() -> dict:
    return {
        "services": SERVICES,
        "uiComponents": UI_COMPONENTS,
        "apiContracts": API_CONTRACTS,
    }


def build_demo_request(method: str, path: str) -> tuple[dict, dict]:
    contract = _match_contract(method, path)
    if not contract:
        return {}, {}
    behavior = _behavior_for_contract(contract)
    if behavior.get("mode") in {"delegated-auth", "authenticate"}:
        return {"email": "demo@example.com", "password": "password123"}, {}

    payload = {}
    query = {}
    for argument in behavior.get("arguments", []):
        name = argument.get("name")
        if not name:
            continue
        value = _example_value(argument)
        if method == "GET":
            query[name] = value
        else:
            payload[name] = value
    if method != "GET" and not payload:
        payload = {"demo": True}
    return payload, query


def invoke_contract(method: str, path: str, payload: dict | None = None, query: dict | None = None) -> tuple[int, dict]:
    payload = payload or {}
    query = query or {}
    contract = _match_contract(method, path)
    if not contract:
        return 404, {"error": "Not found", "path": path, "method": method}

    behavior = _behavior_for_contract(contract)
    service_payload = {
        "service": contract["service"],
        "path": contract["path"],
        "source": contract["source"],
        "method": contract["method"],
    }
    request_data = payload if method != "GET" else query
    errors = _missing_required_arguments(behavior, request_data)
    if errors:
        return 400, {
            **service_payload,
            "error": f"Missing required fields: {', '.join(errors)}",
            "missing": errors,
        }

    if behavior.get("mode") in {"delegated-auth", "authenticate"}:
        return _invoke_auth(service_payload, behavior, payload)
    if _looks_like_order_create(behavior):
        return _invoke_order_create(service_payload, behavior, payload)
    if _looks_like_order_cancel(behavior):
        return _invoke_order_cancel(service_payload, behavior, payload)
    if _looks_like_user_lookup(behavior):
        return _invoke_user_lookup(service_payload, behavior, query)
    if _looks_like_profile_update(behavior):
        return _invoke_profile_update(service_payload, behavior, payload)
    if behavior.get("mode") == "read" or method == "GET":
        return _invoke_read(service_payload, behavior, query)
    if behavior.get("mode") == "create":
        return 201, _invoke_mutation(service_payload, behavior, payload, result_key="created")
    if behavior.get("mode") == "update":
        return 200, _invoke_mutation(service_payload, behavior, payload, result_key="updated")
    if behavior.get("mode") == "delete":
        return 200, _invoke_mutation(service_payload, behavior, payload, result_key="deleted")
    if behavior.get("mode") == "action":
        return 200, _invoke_mutation(service_payload, behavior, payload, result_key="completed")
    return 200, _invoke_mutation(service_payload, behavior, payload, result_key="accepted")


def _behavior_for_contract(contract: dict) -> dict:
    key = f"{contract['method']} {contract['path']}"
    return BEHAVIOR_CATALOG.get("contracts", {}).get(key, {})


def _missing_required_arguments(behavior: dict, data: dict) -> list[str]:
    missing = []
    for argument in behavior.get("arguments", []):
        name = argument.get("name")
        if not name or not argument.get("required"):
            continue
        value = data.get(name)
        if value in (None, ""):
            missing.append(name)
    return missing


def _invoke_auth(service_payload: dict, behavior: dict, payload: dict) -> tuple[int, dict]:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if not email or not password:
        return 400, {
            **service_payload,
            "error": "Email and password are required.",
        }

    user = _find_auth_user(email)
    if not user:
        return 401, {
            **service_payload,
            "error": behavior.get("errorMessages", {}).get("InvalidCredentials", "Invalid credentials."),
            "errorType": "InvalidCredentials",
        }
    if user.get("locked"):
        return 423, {
            **service_payload,
            "error": behavior.get("errorMessages", {}).get("AccountLocked", "Account is locked."),
            "errorType": "AccountLocked",
        }
    if password != user.get("password"):
        attempts = RUNTIME_STATE["failedAttempts"].get(email, 0) + 1
        RUNTIME_STATE["failedAttempts"][email] = attempts
        if attempts >= 3:
            user["locked"] = True
            return 423, {
                **service_payload,
                "error": behavior.get("errorMessages", {}).get("AccountLocked", "Account is locked."),
                "errorType": "AccountLocked",
            }
        return 401, {
            **service_payload,
            "error": behavior.get("errorMessages", {}).get("InvalidCredentials", "Invalid credentials."),
            "errorType": "InvalidCredentials",
        }

    RUNTIME_STATE["failedAttempts"][email] = 0
    return 200, {
        **service_payload,
        "authenticated": True,
        "redirect": behavior.get("redirect"),
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "role": user.get("role"),
        },
        "session": user.get("session", {}),
    }


def _invoke_order_create(service_payload: dict, behavior: dict, payload: dict) -> tuple[int, dict]:
    items = payload.get("items") or []
    user_id = int(payload.get("userId", 101))
    if not isinstance(items, list) or not items:
        return 400, {
            **service_payload,
            "error": "At least one order item is required.",
        }

    normalized_items = []
    total = 0.0
    for item in items:
        product_id = int(item.get("productId", 0))
        quantity = int(item.get("quantity", 0))
        product = _find_product(product_id)
        if not product:
            return 404, {
                **service_payload,
                "error": f"Product {product_id} was not found.",
                "errorType": "ProductNotFound",
            }
        if quantity <= 0:
            return 400, {
                **service_payload,
                "error": "Item quantity must be greater than zero.",
            }
        if product["stock_quantity"] < quantity:
            return 409, {
                **service_payload,
                "error": "Not enough stock for one or more products.",
                "errorType": "InsufficientStock",
            }
        unit_price = float(item.get("unitPrice", product["price"]))
        normalized_items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
            }
        )
        total += unit_price * quantity

    if total > 10000:
        total *= 0.95

    order_id = RUNTIME_STATE["nextOrderId"]
    RUNTIME_STATE["nextOrderId"] += 1
    for item in normalized_items:
        product = _find_product(item["product_id"])
        product["stock_quantity"] -= item["quantity"]

    order = {
        "id": order_id,
        "user_id": user_id,
        "status": "pending",
        "total": round(total, 2),
        "created_at": _now_iso(),
        "items": normalized_items,
    }
    RUNTIME_STATE["orders"].append(order)
    return 201, {
        **service_payload,
        "created": True,
        "orderId": order_id,
        "order": {
            "id": order_id,
            "userId": user_id,
            "status": "pending",
            "total": round(total, 2),
            "itemCount": sum(item["quantity"] for item in normalized_items),
        },
        "tables": behavior.get("tables", []),
    }


def _invoke_order_cancel(service_payload: dict, behavior: dict, payload: dict) -> tuple[int, dict]:
    order_id = int(payload.get("orderId", 0))
    user_id = int(payload.get("userId", 0))
    order = _find_order(order_id)
    if not order:
        return 404, {
            **service_payload,
            "error": "Order not found.",
            "errorType": "OrderNotFound",
        }
    if order["user_id"] != user_id:
        return 403, {
            **service_payload,
            "error": "Not your order.",
            "errorType": "Unauthorized",
        }
    if order["status"] != "pending":
        return 409, {
            **service_payload,
            "error": "Only pending orders can be cancelled.",
            "errorType": "InvalidState",
        }
    for item in order.get("items", []):
        product = _find_product(item["product_id"])
        if product:
            product["stock_quantity"] += item["quantity"]
    order["status"] = "cancelled"
    return 200, {
        **service_payload,
        "completed": True,
        "order": {
            "id": order["id"],
            "userId": order["user_id"],
            "status": order["status"],
            "total": order["total"],
        },
        "tables": behavior.get("tables", []),
    }


def _invoke_user_lookup(service_payload: dict, behavior: dict, query: dict) -> tuple[int, dict]:
    user_id = int(query.get("userId", 101))
    user = _find_auth_user_by_id(user_id)
    if not user:
        return 404, {
            **service_payload,
            "error": "User not found.",
            "errorType": "UserNotFound",
        }
    return 200, {
        **service_payload,
        "item": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
        "tables": behavior.get("tables", []),
    }


def _invoke_profile_update(service_payload: dict, behavior: dict, payload: dict) -> tuple[int, dict]:
    user_id = int(payload.get("userId", 101))
    email = str(payload.get("email", "")).strip().lower()
    user = _find_auth_user_by_id(user_id)
    if not user:
        return 404, {
            **service_payload,
            "error": "User not found.",
            "errorType": "UserNotFound",
        }
    duplicate = _find_auth_user(email)
    if duplicate and duplicate["id"] != user_id:
        return 409, {
            **service_payload,
            "error": "Email already in use.",
            "errorType": "DuplicateEmail",
        }
    if email:
        user["email"] = email
        user.setdefault("session", {})["userEmail"] = email
    for field in ("firstName", "lastName"):
        if payload.get(field) is not None:
            user[field] = payload.get(field)
    return 200, {
        **service_payload,
        "updated": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "firstName": user.get("firstName"),
            "lastName": user.get("lastName"),
        },
        "stateEffects": behavior.get("sessionWrites", []),
        "tables": behavior.get("tables", []),
    }


def _invoke_read(service_payload: dict, behavior: dict, query: dict) -> tuple[int, dict]:
    if _looks_like_order_list(behavior):
        user_id = int(query.get("userId", 101))
        items = []
        for order in RUNTIME_STATE["orders"]:
            if order["user_id"] != user_id:
                continue
            items.append(
                {
                    "id": order["id"],
                    "total": order["total"],
                    "status": order["status"],
                    "item_count": sum(item["quantity"] for item in order.get("items", [])),
                    "created_at": order["created_at"],
                }
            )
        return 200, {
            **service_payload,
            "items": items,
            "tables": behavior.get("tables", []),
        }

    resource_name = _resource_name(service_payload["path"])
    return 200, {
        **service_payload,
        "items": [
            {
                "resource": resource_name,
                "tables": behavior.get("tables", []),
                "query": query,
                "sourceFunction": behavior.get("sourceFunction"),
                "sample": True,
            }
        ],
    }


def _invoke_mutation(service_payload: dict, behavior: dict, payload: dict, result_key: str) -> dict:
    response = {
        **service_payload,
        result_key: True,
        "payload": payload,
        "tables": behavior.get("tables", []),
    }
    throws = behavior.get("throws", [])
    if throws:
        response["possibleErrors"] = throws
    session_writes = behavior.get("sessionWrites", [])
    if session_writes:
        response["stateEffects"] = session_writes
    return response


def _looks_like_order_create(behavior: dict) -> bool:
    arg_names = {arg.get("name") for arg in behavior.get("arguments", [])}
    tables = set(behavior.get("tables", []))
    return behavior.get("mode") == "create" and {"orders", "order_items"} <= tables and "items" in arg_names


def _looks_like_order_cancel(behavior: dict) -> bool:
    throws = set(behavior.get("throws", []))
    return behavior.get("mode") == "action" and {"OrderNotFound", "Unauthorized", "InvalidState"} <= throws


def _looks_like_order_list(behavior: dict) -> bool:
    tables = set(behavior.get("tables", []))
    return behavior.get("mode") == "read" and "orders" in tables


def _looks_like_user_lookup(behavior: dict) -> bool:
    arg_names = {arg.get("name") for arg in behavior.get("arguments", [])}
    tables = set(behavior.get("tables", []))
    return behavior.get("mode") == "read" and tables == {"users"} and "userId" in arg_names


def _looks_like_profile_update(behavior: dict) -> bool:
    arg_names = {arg.get("name") for arg in behavior.get("arguments", [])}
    tables = set(behavior.get("tables", []))
    return behavior.get("mode") == "update" and "users" in tables and {"userId", "email"} <= arg_names


def _find_auth_user(email: str) -> dict | None:
    for user in RUNTIME_STATE["authUsers"]:
        if str(user.get("email", "")).lower() == email:
            return user
    return None


def _find_auth_user_by_id(user_id: int) -> dict | None:
    for user in RUNTIME_STATE["authUsers"]:
        if int(user.get("id", 0)) == user_id:
            return user
    return None


def _find_product(product_id: int) -> dict | None:
    for product in RUNTIME_STATE["products"]:
        if int(product.get("id", 0)) == product_id:
            return product
    return None


def _find_order(order_id: int) -> dict | None:
    for order in RUNTIME_STATE["orders"]:
        if int(order.get("id", 0)) == order_id:
            return order
    return None


def _example_value(argument: dict):
    arg_type = str(argument.get("type", "")).lower()
    name = str(argument.get("name", "")).lower()
    if name == "email":
        return "demo@example.com"
    if name == "password":
        return "password123"
    if name == "userid":
        return 101
    if name == "orderid":
        return 2001
    if arg_type in {"numeric", "integer"}:
        return 1
    if arg_type == "array":
        return [{"productId": 1, "quantity": 1}]
    return f"demo-{name or 'value'}"


def _match_contract(method: str, path: str) -> dict | None:
    for contract in API_CONTRACTS:
        if contract["method"] != method:
            continue
        if _path_matches(contract["path"], path):
            return contract
    return None


def _path_matches(template: str, actual: str) -> bool:
    if template == actual:
        return True
    template_parts = template.strip("/").split("/")
    actual_parts = actual.strip("/").split("/")
    if len(template_parts) != len(actual_parts):
        return False
    for template_part, actual_part in zip(template_parts, actual_parts):
        if template_part.startswith("{") and template_part.endswith("}"):
            continue
        if template_part != actual_part:
            return False
    return True


def _resource_name(path: str) -> str:
    parts = [part for part in path.strip("/").split("/") if not part.startswith("{")]
    return parts[-1] if parts else "resource"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
"""


def _server_py() -> str:
    return """from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app_logic import get_runtime_summary, invoke_contract, list_contracts


FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"


class DemoHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if parsed.path == "/api/meta":
            self._send_json(200, {"runtime": get_runtime_summary(), "contracts": list_contracts()})
            return
        if parsed.path in {"/", "/index.html"}:
            self._send_file(FRONTEND_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._send_file(FRONTEND_ROOT / "app.js", "text/javascript; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._send_file(FRONTEND_ROOT / "styles.css", "text/css; charset=utf-8")
            return
        status, payload = invoke_contract("GET", parsed.path, query={key: values[0] for key, values in parse_qs(parsed.query).items()})
        self._send_json(status, payload)

    def do_POST(self) -> None:
        self._handle_mutating("POST")

    def do_PUT(self) -> None:
        self._handle_mutating("PUT")

    def do_PATCH(self) -> None:
        self._handle_mutating("PATCH")

    def do_DELETE(self) -> None:
        self._handle_mutating("DELETE")

    def _handle_mutating(self, method: str) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        status, response_payload = invoke_contract(method, parsed.path, payload=payload)
        self._send_json(status, response_payload)


def run(port: int | None = None) -> None:
    if port is None:
        parser = argparse.ArgumentParser(description="Run the generated modernization demo app.")
        parser.add_argument("--port", type=int, default=None, help="Port to bind the demo server to.")
        args = parser.parse_args()
        port = args.port
    if port is None:
        port = int(os.environ.get("MODERNIZE_DEMO_PORT", "8787"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoHandler)
    print(f"demo server listening on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
"""


def _backend_readme(app_name: str) -> str:
    return f"""# {app_name} Backend

Run the backend with:

```bash
python3 backend/server.py --port 8787
```

The backend serves generated API contracts plus the generated frontend.
"""


def _frontend_index_html(app_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{app_name}</title>
    <link rel="stylesheet" href="/styles.css" />
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="text/babel" data-presets="env,react" src="/app.js"></script>
  </body>
</html>
"""


def _frontend_styles_css() -> str:
    return """body {
  margin: 0;
  font-family: "Avenir Next", "Segoe UI", sans-serif;
  background: linear-gradient(180deg, #f7efe4, #fffaf4);
  color: #1f2a37;
}

.shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
}

.login-shell {
  background: #fff;
  border: 1px solid #e9d2af;
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 16px 42px rgba(73, 42, 13, 0.08);
  width: min(100%, 420px);
}

.login-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.login-eyebrow {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
  color: #8d4810;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.login-title {
  margin: 0;
  font-size: 2rem;
}

.login-subtitle {
  margin: 0;
  color: #667085;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field label {
  font-weight: 600;
}

.field input {
  border: 1px solid #d6c3a3;
  border-radius: 12px;
  padding: 12px 14px;
  font: inherit;
}

.field small {
  color: #7a5a36;
}

.error-banner {
  background: #fff1ef;
  color: #9f2d20;
  border: 1px solid #f3b8ae;
  border-radius: 12px;
  padding: 12px 14px;
}

.status-banner {
  background: #eef6ff;
  color: #144d7a;
  border: 1px solid #b9d8f4;
  border-radius: 12px;
  padding: 12px 14px;
}

.form-links {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.form-links a {
  color: #8d4810;
  text-decoration: none;
  font-weight: 600;
}

button {
  background: #be5f16;
  color: white;
  border: none;
  border-radius: 12px;
  padding: 12px 16px;
  cursor: pointer;
}

.muted {
  color: #667085;
}

.redirect-note {
  margin: 0;
  color: #667085;
  font-size: 0.95rem;
}

.dashboard-panel {
  background: #f8f2e8;
  border: 1px solid #e4cfad;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dashboard-panel p {
  margin: 0;
}
"""


def _frontend_app_js() -> str:
    return """const { useEffect, useState } = React;

function App() {
  const [runtime, setRuntime] = useState(null);
  const [formState, setFormState] = useState({});
  const [error, setError] = useState(primaryErrorMessage());
  const [notice, setNotice] = useState("");
  const [screen, setScreen] = useState("login");
  const [authResult, setAuthResult] = useState(null);

  const loadMeta = async () => {
    const response = await fetch("/api/meta");
    const payload = await response.json();
    setRuntime(payload);
  };

  useEffect(() => {
    loadMeta();
  }, []);

  const primaryPage = runtime?.runtime.uiComponents?.[0];
  const primaryForm = primaryPage?.forms?.[0];
  const formInputs = primaryForm?.inputs || [];
  const loginContract =
    runtime?.contracts?.find((item) => item.path === "/login" && item.method === "POST") ||
    runtime?.contracts?.find((item) => item.method === "POST");

  const handleFieldChange = (name, value) => {
    setFormState((current) => ({ ...current, [name]: value }));
  };

  const runContract = async (contract, requestPayload) => {
    if (!runtime || !contract) {
      setNotice("");
      setError("No generated login contract is available.");
      return;
    }
    const response = await fetch(contract.path.replace("{id}", "1").replace("{user_id}", "1"), {
      method: contract.method,
      headers: { "Content-Type": "application/json" },
      body: contract.method === "GET" ? undefined : JSON.stringify(requestPayload || { demo: true, source: contract.source }),
    });
    const responsePayload = await response.json();
    if (!response.ok) {
      setNotice("");
      setError(responsePayload.error || "Request failed.");
      return;
    }
    setError("");
    if (contract.path === "/login" && responsePayload?.authenticated) {
      setAuthResult(responsePayload);
      setScreen("post-login");
      setNotice("");
      return;
    }
    setNotice(buildNotice(contract, responsePayload, primaryPage));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!loginContract) {
      setError("No generated login contract is available.");
      return;
    }
    setNotice("");
    await runContract(loginContract, formState);
  };

  return (
    <div className="shell">
      <div className="login-shell">
        <div className="login-card">
          {screen === "post-login" ? (
            <PostLoginView
              primaryPage={primaryPage}
              authResult={authResult}
              onSignOut={() => {
                setScreen("login");
                setAuthResult(null);
                setFormState({});
              }}
            />
          ) : (
            <>
              <p className="login-eyebrow">{primaryPage?.title || "Application"}</p>
              <h1 className="login-title">{primaryPage?.headings?.[0] || primaryPage?.name || "Sign In"}</h1>
              <p className="login-subtitle">Enter your credentials to continue.</p>
              {error ? <div className="error-banner">{error}</div> : null}
              {notice ? <div className="status-banner">{notice}</div> : null}
              {primaryForm ? (
                <form onSubmit={handleSubmit}>
                  {formInputs.map((input) => (
                    <div className="field" key={input.name || input.id}>
                      <label htmlFor={input.id || input.name}>{input.label || toLabel(input.name || input.id || "Field")}</label>
                      <input
                        id={input.id || input.name}
                        name={input.name || input.id}
                        type={input.type || "text"}
                        required={Boolean(input.required)}
                        value={formState[input.name || input.id] || ""}
                        onChange={(event) => handleFieldChange(input.name || input.id, event.target.value)}
                      />
                      {input.message ? <small>{input.message}</small> : null}
                    </div>
                  ))}
                  <button type="submit">{primaryForm.submitLabels?.[0] || "Submit"}</button>
                </form>
              ) : (
                <p>No source form evidence was available for this page.</p>
              )}
              {primaryPage?.links?.length ? (
                <div className="form-links">
                  {primaryPage.links.map((link) => (
                    <a key={link.href} href={link.href}>
                      {link.text || link.href}
                    </a>
                  ))}
                </div>
              ) : null}
              {primaryPage?.redirects?.length ? (
                <p className="redirect-note">Successful sign-in redirects to {primaryPage.redirects.join(", ")}.</p>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function PostLoginView({ primaryPage, authResult, onSignOut }) {
  const redirectTarget = authResult?.redirect || primaryPage?.redirects?.[0] || "/dashboard";
  const redirectLabel = toLabel(redirectTarget.split("/").filter(Boolean).pop() || "dashboard");
  return (
    <>
      <p className="login-eyebrow">{redirectLabel}</p>
      <h1 className="login-title">Welcome back</h1>
      <p className="login-subtitle">The generated app followed the source redirect intent after successful authentication.</p>
      <div className="status-banner">
        Signed in as <strong>{authResult?.user?.email || "user"}</strong>.
      </div>
      <div className="dashboard-panel">
        <p><strong>Destination:</strong> {redirectTarget}</p>
        <p><strong>User ID:</strong> {authResult?.user?.id ?? "n/a"}</p>
        <p><strong>Role:</strong> {authResult?.user?.role || "n/a"}</p>
      </div>
      <button type="button" onClick={onSignOut}>Sign Out</button>
    </>
  );
}

function primaryErrorMessage() {
  return "";
}

function buildNotice(contract, responsePayload, primaryPage) {
  const redirectTarget = primaryPage?.redirects?.[0];
  if (contract.path === "/login" && redirectTarget) {
    return `Sign-in accepted. Next destination: ${redirectTarget}`;
  }
  if (responsePayload?.accepted) {
    return "Request accepted.";
  }
  if (responsePayload?.updated) {
    return "Changes saved.";
  }
  if (responsePayload?.deleted) {
    return "Item removed.";
  }
  return "Request completed.";
}

function toLabel(value) {
  return String(value)
    .replace(/[-_]/g, " ")
    .replace(/\\b\\w/g, (match) => match.toUpperCase());
}

const rootElement = document.getElementById("root");
if (ReactDOM.createRoot) {
  ReactDOM.createRoot(rootElement).render(<App />);
} else {
  ReactDOM.render(<App />, rootElement);
}
"""
