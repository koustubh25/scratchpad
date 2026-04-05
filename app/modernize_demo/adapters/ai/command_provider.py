"""Adapter that delegates semantic derivation to an arbitrary local command."""

from __future__ import annotations

import json
import os
import shlex
import subprocess

from .base import GeneratedApplication, SemanticDerivation


class CommandJSONProvider:
    """Run a local command that accepts stdin JSON and returns stdout JSON."""

    name = "command-json"

    def __init__(self, command: str, timeout_seconds: int = 90) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "CommandJSONProvider":
        command = os.environ.get("MODERNIZE_AI_COMMAND")
        if not command:
            raise RuntimeError(
                "provider 'command-json' requires MODERNIZE_AI_COMMAND to be set to a command "
                "that reads JSON from stdin and writes JSON to stdout"
            )
        timeout_seconds = int(os.environ.get("MODERNIZE_AI_TIMEOUT_SECONDS", "90"))
        return cls(command=command, timeout_seconds=timeout_seconds)

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        payload = {
            "task": "derive_semantics",
            "facts": facts,
            "outputSchema": {
                "summary": "string",
                "moduleRole": "string",
                "businessCapabilities": [
                    {"function": "string", "description": "string", "confidence": "0..100 int"}
                ],
                "confidence": "0..100 int",
                "fieldConfidences": {
                    "summary": "0..100 int",
                    "moduleRole": "0..100 int",
                    "businessCapabilities": "0..100 int",
                },
            },
        }
        completed = subprocess.run(
            shlex.split(self.command),
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"command-json provider failed with exit code {completed.returncode}: {completed.stderr.strip()}"
            )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("command-json provider returned invalid JSON") from exc

        return SemanticDerivation(
            summary=response["summary"],
            module_role=response["moduleRole"],
            business_capabilities=_normalize_capabilities(response["businessCapabilities"]),
            confidence=int(response["confidence"]),
            field_confidences={
                "summary": int(response["fieldConfidences"]["summary"]),
                "moduleRole": int(response["fieldConfidences"]["moduleRole"]),
                "businessCapabilities": int(response["fieldConfidences"]["businessCapabilities"]),
            },
            provider=self.name,
        )

    def generate_application(self, generation_context: dict) -> GeneratedApplication:
        payload = {
            "task": "generate_application_files",
            "generationContext": generation_context,
            "outputSchema": {
                "files": [{"path": "string", "content": "string"}],
                "notes": ["string"],
            },
        }
        completed = subprocess.run(
            shlex.split(self.command),
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"command-json provider failed with exit code {completed.returncode}: {completed.stderr.strip()}"
            )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("command-json provider returned invalid JSON") from exc

        return GeneratedApplication(
            files={item["path"]: item["content"] for item in response["files"]},
            provider=self.name,
            notes=list(response.get("notes", [])),
        )


def _normalize_capabilities(items: list[dict]) -> list[dict]:
    normalized = []
    for item in items:
        normalized.append(
            {
                "function": item["function"],
                "description": item["description"],
                "source": "ai",
                "confidence": int(item["confidence"]),
            }
        )
    return normalized
