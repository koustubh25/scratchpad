"""Provider tests for pluggable semantic AI adapters."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modernize import run_cli
from modernize_demo.adapters.ai.command_provider import CommandJSONProvider
from modernize_demo.adapters.ai.registry import load_provider
from modernize_demo.core.state import ProjectState


class AIProviderTests(unittest.TestCase):
    """Verify provider loading and command-driven semantic derivation."""

    def test_command_json_provider_returns_structured_semantics(self) -> None:
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "providers" / "semantic_command_provider.py"
        with patch.dict(os.environ, {"MODERNIZE_AI_COMMAND": f"python3 {fixture}"}):
            provider = CommandJSONProvider.from_environment()
            result = provider.derive_semantics(
                {
                    "module": "login",
                    "functions": [{"name": "render_login"}],
                }
            )

        self.assertEqual(result.module_role, "command-derived-role")
        self.assertEqual(result.provider, "command-json")
        self.assertEqual(result.field_confidences["summary"], 89)

    def test_python_provider_spec_loads_custom_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            source_root = project_root / "fixtures"
            source_root.mkdir()
            (source_root / "login.cfm").write_text("<cfif true></cfif>", encoding="utf-8")

            exit_code = run_cli(
                [
                    "init",
                    str(source_root),
                    "--provider",
                    "python:modernize_demo.adapters.ai.demo_provider:DemoAIProvider",
                ],
                project_root=project_root,
            )

            self.assertEqual(exit_code, 0)
            provider = load_provider(ProjectState(project_root))
            self.assertEqual(provider.name, "demo-ai")


if __name__ == "__main__":
    unittest.main()
