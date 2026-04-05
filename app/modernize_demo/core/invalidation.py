"""Stale lock detection based on upstream discovery and artifact hashes."""

from __future__ import annotations

from typing import Any

from .hashing import sha256_json
from .state import ProjectState


def current_discovery_fingerprint(state: ProjectState) -> str | None:
    """Return the current discovery fingerprint when discovery has run."""
    discovery = state.read_json("discovery", "source-discovery.json")
    if not discovery:
        return None
    return discovery.get("sourceHashSummary")


def artifact_fingerprint(state: ProjectState, subdir: str, filename: str) -> str | None:
    """Hash an artifact if it exists."""
    artifact = state.read_json(subdir, filename)
    if artifact is None:
        return None
    return sha256_json(artifact)


def lock_is_stale(state: ProjectState, lock_name: str) -> tuple[bool, str]:
    """Return whether a lock is stale and why."""
    lock = state.read_json("locked", lock_name)
    if not lock:
        return True, "missing lock"

    expected = lock.get("sourceDiscoveryFingerprint")
    current = current_discovery_fingerprint(state)
    if expected and current and expected != current:
        return True, "source or config discovery changed"

    checks = lock.get("artifactFingerprints", {})
    for artifact_path, expected_hash in checks.items():
        subdir, filename = artifact_path.split("/", 1)
        current_hash = artifact_fingerprint(state, subdir, filename)
        if current_hash != expected_hash:
            return True, f"artifact changed: {artifact_path}"

    return False, "fresh"

