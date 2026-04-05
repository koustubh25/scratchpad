"""Verification support for generated applications."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ..core.audit import log_event, now_iso
from ..core.state import ProjectState


def run_verify(state: ProjectState, app_name: str) -> dict:
    """Run lightweight scenario-based verification against generated logic."""
    service_root = state.path_for("services", app_name)
    logic_path = service_root / "backend" / "app_logic.py"
    if not logic_path.exists():
        raise RuntimeError("generated app does not exist; run generate first")

    module = _load_module(logic_path)
    contracts = module.list_contracts()
    runtime = module.get_runtime_summary()
    scenarios = []

    scenarios.append(
        {
            "name": "runtime summary",
            "status": "PASS" if runtime["services"] else "FAIL",
            "detail": "Generated app exposes at least one backend service.",
        }
    )

    for contract in contracts:
        payload, query = ({}, {"demo": "true"})
        if hasattr(module, "build_demo_request"):
            payload, query = module.build_demo_request(
                contract["method"],
                _materialize_path(contract["path"]),
            )
        status, payload = module.invoke_contract(
            contract["method"],
            _materialize_path(contract["path"]),
            payload=payload,
            query=query,
        )
        scenarios.append(
            {
                "name": f"{contract['method']} {contract['path']}",
                "status": "PASS" if status < 400 and payload.get("service") == contract["service"] else "FAIL",
                "detail": f"Generated contract {contract['source']} responds through {contract['service']}.",
            }
        )

    verdict = "PASS" if all(item["status"] == "PASS" for item in scenarios) else "FAIL"
    report = {
        "appName": app_name,
        "verifiedAt": now_iso(),
        "verdict": verdict,
        "scenarios": scenarios,
    }
    state.write_json(f"recordings/{app_name}", "verification-report.json", report)
    state.update_step("verify", "completed", appName=app_name, verdict=verdict)
    log_event(state, "stage.completed", stage="verify", appName=app_name, verdict=verdict)
    return report


def _materialize_path(path: str) -> str:
    return path.replace("{user_id}", "1").replace("{id}", "1")


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("generated_app_logic", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module
