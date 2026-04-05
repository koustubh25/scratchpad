"""Offline heuristic provider kept as an explicit demo fallback."""

from __future__ import annotations

from .base import GeneratedApplication, SemanticDerivation


class DemoAIProvider:
    """Deterministic fallback provider for local demos and tests."""

    name = "demo-ai"

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        module = facts["module"]
        tables = sorted({entry["table"] for entry in facts["tables_touched"]})
        role = _infer_module_role(module, tables, facts["module_type"])
        summary = _infer_summary(module, role, facts)
        capabilities = []
        for function in facts["functions"]:
            capabilities.append(
                {
                    "function": function["name"],
                    "description": _describe_function(function, module),
                    "source": "ai",
                    "confidence": 84 if function["tables"] or function["throws"] else 78,
                }
            )
        return SemanticDerivation(
            summary=summary,
            module_role=role,
            business_capabilities=capabilities,
            confidence=min(92, max(78, 80 + len(tables))),
            field_confidences={
                "summary": 86,
                "moduleRole": 98,
                "businessCapabilities": 82,
            },
            provider=self.name,
        )

    def generate_application(self, generation_context: dict) -> GeneratedApplication:
        files = generation_context["deterministicFallbackFiles"]
        return GeneratedApplication(
            files=files,
            provider=self.name,
            notes=[
                "Used deterministic fallback generation because provider is demo-ai.",
            ],
        )


def _infer_module_role(module: str, tables: list[str], module_type: str) -> str:
    name = module.lower()
    if module_type == "template":
        return "request-entrypoint"
    if "user" in name or "auth" in name or "users" in tables:
        return "identity-service"
    if "order" in name or "orders" in tables:
        return "order-service"
    return "domain-service"


def _infer_summary(module: str, role: str, facts: dict) -> str:
    if role == "request-entrypoint":
        endpoint = facts["endpoints"][0]["path"] if facts["endpoints"] else f"/{module.lower()}"
        return f"{module} handles the {endpoint} user-facing flow and delegates core business logic to downstream components."
    tables = ", ".join(sorted({entry['table'] for entry in facts['tables_touched']})) or "application state"
    return f"{module} encapsulates {role.replace('-', ' ')} behavior around {tables} with explicit validation and state transitions."


def _describe_function(function: dict, module: str) -> str:
    tables = ", ".join(function["tables"]) if function["tables"] else "application state"
    if function["throws"]:
        return (
            f"{module}.{function['name']} coordinates business rules around {tables} "
            f"and can surface {', '.join(function['throws'])} conditions."
        )
    return f"{module}.{function['name']} executes deterministic logic over {tables} and its immediate dependencies."
