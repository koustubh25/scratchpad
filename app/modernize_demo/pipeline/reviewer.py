"""Interactive and scripted review support."""

from __future__ import annotations

from pathlib import Path

from ..core.audit import log_event, now_iso
from ..core.rendering import render_template
from ..core.state import ProjectState

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def review_semantics(state: ProjectState, module: str | None = None) -> dict:
    """Return semantic review data for one module or for all modules."""
    review_state = state.read_json("semantics", "review-state.json")
    if not review_state:
        raise RuntimeError("extract must run before review")
    render_semantic_review_documents(state)

    if module:
        semantic = state.read_json("semantics", f"{module}.semantic.json")
        if not semantic:
            raise RuntimeError(f"unknown module: {module}")
        return {
            "module": module,
            "reviewDocument": str(state.path_for("docs", f"semantic-review/modules/{module}.md")),
            "review": semantic["review"],
            "summary": semantic["summary"],
            "moduleRole": semantic["module_role"],
        }
    return {
        "status": review_state["status"],
        "indexDocument": str(state.path_for("docs", "semantic-review/index.md")),
        "modules": [
            {
                "module": module_name,
                "status": module_state["status"],
                "approved": module_state["approved"],
                "reviewDocument": str(state.path_for("docs", f"semantic-review/modules/{module_name}.md")),
            }
            for module_name, module_state in sorted(review_state["modules"].items())
        ],
    }


def correct_semantics(state: ProjectState, module: str, field: str, value: str, reviewer: str = "demo-reviewer") -> dict:
    """Apply a small correction to one semantic artifact."""
    semantic = state.read_json("semantics", f"{module}.semantic.json")
    if not semantic:
        raise RuntimeError(f"unknown module: {module}")

    correction = {
        "field": field,
        "value": value,
        "by": reviewer,
        "at": now_iso(),
    }
    if field == "summary":
        semantic["summary"] = value
        semantic["fields"]["summary"] = {"value": value, "source": "human", "confidence": 100, "provider": "human"}
    elif field == "moduleRole":
        semantic["module_role"] = value
        semantic["fields"]["moduleRole"] = {"value": value, "source": "human", "confidence": 100, "provider": "human"}
    else:
        raise RuntimeError(f"unsupported field for correction: {field}")

    semantic["review"]["corrections"].append(correction)
    state.write_json("semantics", f"{module}.semantic.json", semantic)

    review_state = state.read_json("semantics", "review-state.json")
    review_state["modules"][module]["corrections"].append(correction)
    state.write_json("semantics", "review-state.json", review_state)
    render_semantic_review_documents(state)
    log_event(state, "semantics.corrected", module=module, field=field, reviewer=reviewer)
    return semantic


def approve_semantics(state: ProjectState, module: str | None = None, reviewer: str = "demo-reviewer") -> dict:
    """Approve one or all semantic artifacts."""
    review_state = state.read_json("semantics", "review-state.json")
    if not review_state:
        raise RuntimeError("extract must run before approve")

    modules = [module] if module else sorted(review_state["modules"])
    approved_at = now_iso()
    for module_name in modules:
        semantic = state.read_json("semantics", f"{module_name}.semantic.json")
        if not semantic:
            raise RuntimeError(f"unknown module: {module_name}")
        semantic["review"].update(
            {
                "status": "approved",
                "approved": True,
                "approvedBy": reviewer,
                "approvedAt": approved_at,
            }
        )
        state.write_json("semantics", f"{module_name}.semantic.json", semantic)
        review_state["modules"][module_name].update(
            {
                "status": "approved",
                "approved": True,
                "approvedBy": reviewer,
                "approvedAt": approved_at,
            }
        )
        log_event(state, "semantics.approved", module=module_name, reviewer=reviewer)

    if all(module_state["approved"] for module_state in review_state["modules"].values()):
        review_state["status"] = "approved"
        state.update_step("review_semantics", "completed", approvedModules=len(review_state["modules"]))
    else:
        state.update_step(
            "review_semantics",
            "in_progress",
            approvedModules=sum(1 for module_state in review_state["modules"].values() if module_state["approved"]),
        )
    state.write_json("semantics", "review-state.json", review_state)
    render_semantic_review_documents(state)
    return review_state


def render_semantic_review_documents(state: ProjectState) -> dict:
    """Render scalable semantic review docs: one index and one document per module."""
    review_state = state.read_json("semantics", "review-state.json")
    if not review_state:
        raise RuntimeError("extract must run before rendering semantic review docs")

    slice_manifest = state.read_json("discovery", "demo-slice.json") or {}
    selected_modules = slice_manifest.get("selectedModules", [])
    semantics = []
    for module_name in selected_modules:
        semantic = state.read_json("semantics", f"{module_name}.semantic.json")
        if semantic:
            semantics.append(semantic)
    semantics = sorted(semantics, key=lambda item: item["module"].lower())

    module_entries = []
    for semantic in semantics:
        facts = state.read_json("facts", f"{semantic['module']}.facts.json")
        ast = state.read_json("ast", f"{semantic['module']}.ast.json")
        facts = _merge_review_evidence(facts, ast)
        module_doc_path = state.write_text(
            "docs",
            f"semantic-review/modules/{semantic['module']}.md",
            render_template(
                TEMPLATE_DIR,
                "semantic_review_module.md.j2",
                semantic=semantic,
                facts=facts,
            ),
        )
        module_entries.append(
            {
                "module": semantic["module"],
                "moduleRole": semantic["module_role"],
                "summary": semantic["summary"],
                "confidence": semantic["confidence"],
                "status": semantic["review"]["status"],
                "approved": semantic["review"]["approved"],
                "reviewDocument": str(module_doc_path),
            }
        )

    index_doc_path = state.write_text(
        "docs",
        "semantic-review/index.md",
        render_template(
            TEMPLATE_DIR,
            "semantic_review_index.md.j2",
            review_status=review_state["status"],
            modules=module_entries,
        ),
    )
    return {
        "indexDocument": str(index_doc_path),
        "modules": module_entries,
    }


def _merge_review_evidence(facts: dict | None, ast: dict | None) -> dict:
    """Prefer richer UI evidence from AST when fact artifacts are thinner."""
    facts = facts or {}
    ast = ast or {}
    merged = dict(facts)
    fact_ui = dict(facts.get("ui_evidence", {}) or {})
    ast_ui = dict(ast.get("ui_evidence", {}) or {})

    merged_ui = {**ast_ui, **fact_ui}

    fact_forms = fact_ui.get("forms", []) or []
    ast_forms = ast_ui.get("forms", []) or []
    merged_forms = []
    max_len = max(len(fact_forms), len(ast_forms))
    for index in range(max_len):
        fact_form = fact_forms[index] if index < len(fact_forms) else {}
        ast_form = ast_forms[index] if index < len(ast_forms) else {}
        merged_form = {**ast_form, **fact_form}
        fact_inputs = fact_form.get("inputs", []) or []
        ast_inputs = ast_form.get("inputs", []) or []
        merged_inputs = []
        for input_index in range(max(len(fact_inputs), len(ast_inputs))):
            fact_input = fact_inputs[input_index] if input_index < len(fact_inputs) else {}
            ast_input = ast_inputs[input_index] if input_index < len(ast_inputs) else {}
            merged_inputs.append({**ast_input, **fact_input})
        if merged_inputs:
            merged_form["inputs"] = merged_inputs
        merged_forms.append(merged_form)

    if merged_forms:
        merged_ui["forms"] = merged_forms

    merged["ui_evidence"] = merged_ui
    return merged
