#!/usr/bin/env python3
"""Simple JSON-in/JSON-out semantic provider fixture for tests."""

from __future__ import annotations

import json
import sys


def main() -> int:
    payload = json.loads(sys.stdin.read())
    facts = payload["facts"]
    module = facts["module"]
    functions = facts.get("functions", [])
    capabilities = [
        {
            "function": function["name"],
            "description": f"{module}.{function['name']} capability from command provider.",
            "confidence": 88,
        }
        for function in functions
    ]
    response = {
        "summary": f"{module} summary from command-json provider.",
        "moduleRole": "command-derived-role",
        "businessCapabilities": capabilities,
        "confidence": 87,
        "fieldConfidences": {
            "summary": 89,
            "moduleRole": 91,
            "businessCapabilities": 88,
        },
    }
    sys.stdout.write(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
