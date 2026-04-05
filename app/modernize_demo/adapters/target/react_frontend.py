"""Target-side conventions for generated React frontend output."""

from __future__ import annotations


def conventions() -> dict:
    """Return deterministic target conventions for the React frontend."""
    return {
        "name": "react-frontend-demo-adapter",
        "runtime": "browser",
        "framework": "react-umd-cdn",
        "entrypoint": "frontend/index.html",
        "build": "none-required-for-demo",
        "stateStyle": "local-state-with-fetch",
    }

