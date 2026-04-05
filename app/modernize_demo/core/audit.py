"""Audit logging for stage transitions and approvals."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .state import ProjectState


def now_iso() -> str:
    """Return a timezone-aware ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def log_event(state: ProjectState, event_type: str, **payload: Any) -> None:
    """Append a single audit event to the JSONL audit log."""
    event = {
        "at": now_iso(),
        "eventType": event_type,
        "payload": payload,
    }
    path = state.path_for("audit", "audit-log.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")

