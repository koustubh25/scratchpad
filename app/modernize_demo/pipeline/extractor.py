"""Semantic derivation stage."""

from __future__ import annotations

from ..adapters.ai.registry import load_provider
from ..core.audit import log_event
from ..core.models import SemanticArtifact
from ..core.state import ProjectState
from .reviewer import render_semantic_review_documents


def run_extract(state: ProjectState) -> list[dict]:
    """Derive semantics from fact artifacts."""
    slice_manifest = state.read_json("discovery", "demo-slice.json")
    if not slice_manifest:
        raise RuntimeError("discover must run before extract")

    modules = slice_manifest.get("selectedModules", [])
    fact_files = [state.path_for("facts", f"{module}.facts.json") for module in modules]
    if not fact_files or any(not path.exists() for path in fact_files):
        raise RuntimeError("facts must run before extract")
    provider = load_provider(state)

    selected_modules = set(modules)
    for path in state.list_files("semantics", ".semantic.json"):
        if path.stem.replace(".semantic", "") not in selected_modules:
            path.unlink(missing_ok=True)
    for path in state.list_files("docs", ".md"):
        if "semantic-review/modules/" in str(path.relative_to(state.modernize_dir)):
            module_name = path.stem
            if module_name not in selected_modules:
                path.unlink(missing_ok=True)

    review_state = {
        "status": "in_review",
        "modules": {},
    }
    results = []
    for fact_file in fact_files:
        facts = state.read_json("facts", fact_file.name)
        semantic = derive_semantics(facts, provider)
        results.append(semantic)
        state.write_json("semantics", f"{semantic.module}.semantic.json", semantic)
        review_state["modules"][semantic.module] = {
            "status": "pending",
            "approved": False,
            "corrections": [],
        }

    state.write_json("semantics", "review-state.json", review_state)
    render_semantic_review_documents(state)
    state.update_step("extract", "completed", modules=len(results))
    state.update_step("review_semantics", "pending", modules=len(results))
    log_event(state, "stage.completed", stage="extract", modules=len(results), provider=provider.name)
    return [state.read_json("semantics", f"{item.module}.semantic.json") for item in results]


def derive_semantics(facts: dict, provider) -> SemanticArtifact:
    """Produce a structured semantic artifact from facts using the configured provider."""
    module = facts["module"]
    tables = sorted({entry["table"] for entry in facts["tables_touched"]})
    derivation = provider.derive_semantics(facts)
    fields = {
        "summary": {
            "value": derivation.summary,
            "source": "ai" if provider.name != "demo-ai" else "ai-fallback",
            "confidence": derivation.field_confidences["summary"],
            "provider": provider.name,
        },
        "moduleRole": {
            "value": derivation.module_role,
            "source": "ai" if provider.name != "demo-ai" else "ai-fallback",
            "confidence": derivation.field_confidences["moduleRole"],
            "provider": provider.name,
        },
        "businessCapabilities": {
            "value": derivation.business_capabilities,
            "source": "ai" if provider.name != "demo-ai" else "ai-fallback",
            "confidence": derivation.field_confidences["businessCapabilities"],
            "provider": provider.name,
        },
    }

    return SemanticArtifact(
        module=module,
        file_path=facts["file_path"],
        summary=derivation.summary,
        module_role=derivation.module_role,
        business_capabilities=derivation.business_capabilities,
        dependencies=facts["dependencies"],
        data_touch_points=tables,
        confidence=derivation.confidence,
        fields=fields,
        review={
            "status": "pending",
            "approved": False,
            "approvedBy": None,
            "approvedAt": None,
            "corrections": [],
        },
    )
