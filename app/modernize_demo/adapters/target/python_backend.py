"""Target-side conventions for generated Python backend output."""

from __future__ import annotations


def conventions() -> dict:
    """Return deterministic target conventions for the Python backend."""
    return {
        "name": "python-backend-demo-adapter",
        "runtime": "python3.11",
        "framework": "standard-library-http-server",
        "entrypoint": "backend/server.py",
        "apiStyle": "json-http",
        "testing": "unittest + urllib",
    }

