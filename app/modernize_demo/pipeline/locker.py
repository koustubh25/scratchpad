"""Lock creation and stale detection."""

from __future__ import annotations

from ..core.audit import log_event, now_iso
from ..core.hashing import sha256_json
from ..core.invalidation import current_discovery_fingerprint
from ..core.state import ProjectState


def lock_semantics(state: ProjectState, reviewer: str = "demo-reviewer") -> dict:
    """Freeze approved semantic artifacts into a semantic lock."""
    review_state = state.read_json("semantics", "review-state.json")
    if not review_state:
        raise RuntimeError("semantic review state is missing")
    if not all(module_state["approved"] for module_state in review_state["modules"].values()):
        raise RuntimeError("all semantic modules must be approved before lock")

    module_checksums = {}
    artifact_fingerprints = {}
    locked_modules = {}
    for module in sorted(review_state["modules"]):
        semantic = state.read_json("semantics", f"{module}.semantic.json")
        fingerprint = sha256_json(semantic)
        artifact_fingerprints[f"semantics/{module}.semantic.json"] = fingerprint
        module_checksums[module] = fingerprint
        locked_modules[module] = {
            "checksum": fingerprint,
            "approvedBy": semantic["review"]["approvedBy"],
            "approvedAt": semantic["review"]["approvedAt"],
        }

    lock = {
        "lockType": "semantic",
        "version": "1.0",
        "lockedAt": now_iso(),
        "lockedBy": reviewer,
        "sourceDiscoveryFingerprint": current_discovery_fingerprint(state),
        "artifactFingerprints": artifact_fingerprints,
        "modules": locked_modules,
    }
    state.write_json("locked", "semantic-lock.json", lock)

    manifest = state.read_json("locked", "lock-manifest.json") or {}
    manifest["semanticLock"] = {
        "lockedAt": lock["lockedAt"],
        "moduleCount": len(locked_modules),
        "sourceDiscoveryFingerprint": lock["sourceDiscoveryFingerprint"],
    }
    state.write_json("locked", "lock-manifest.json", manifest)
    state.update_step("lock_semantics", "completed", modules=len(locked_modules))
    log_event(state, "lock.created", lockType="semantic", reviewer=reviewer, modules=len(locked_modules))
    return lock

