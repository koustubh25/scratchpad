"""Hashing helpers for artifact lineage and stale detection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_text(value: str) -> str:
    """Return a stable sha256 fingerprint for text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(data: Any) -> str:
    """Return a stable sha256 fingerprint for JSON-serializable data."""
    rendered = json.dumps(data, sort_keys=True, indent=2)
    return sha256_text(rendered)


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

