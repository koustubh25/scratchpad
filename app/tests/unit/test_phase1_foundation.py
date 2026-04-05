"""Phase 1 tests: initialization and project state."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modernize import run_cli
from modernize_demo.core.state import ProjectState


class FoundationTests(unittest.TestCase):
    """Verify basic project bootstrapping."""

    def test_init_creates_state_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            source_root = project_root / "fixtures"
            source_root.mkdir()
            (source_root / "login.cfm").write_text("<cfif true></cfif>", encoding="utf-8")

            exit_code = run_cli(
                [
                    "init",
                    str(source_root),
                ],
                project_root=project_root,
            )

            self.assertEqual(exit_code, 0)
            state = ProjectState(project_root)
            self.assertTrue(state.is_initialized)
            migration = state.load_migration()
            self.assertEqual(migration["project"]["source_language"], "coldfusion")
            self.assertEqual(migration["project"]["target_stack"], [])
            for subdir in ProjectState.SUBDIRECTORIES:
                self.assertTrue((state.modernize_dir / subdir).exists(), msg=subdir)

    def test_choose_provider_updates_project_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            source_root = project_root / "fixtures"
            source_root.mkdir()
            (source_root / "login.cfm").write_text("<cfif true></cfif>", encoding="utf-8")

            self.assertEqual(run_cli(["init", str(source_root)], project_root=project_root), 0)
            self.assertEqual(
                run_cli(["choose-provider", "--provider", "command-json"], project_root=project_root),
                0,
            )

            migration = ProjectState(project_root).load_migration()
            self.assertEqual(migration["project"]["provider"], "command-json")

    def test_choose_target_stack_persists_architecture_and_deployment_style(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            source_root = project_root / "fixtures"
            source_root.mkdir()
            (source_root / "login.cfm").write_text("<cfif true></cfif>", encoding="utf-8")

            self.assertEqual(run_cli(["init", str(source_root)], project_root=project_root), 0)
            state = ProjectState(project_root)
            state.update_step("lock_source_architecture", "completed")

            self.assertEqual(
                run_cli(
                    [
                        "choose-target-stack",
                        "--target-stack",
                        "python:backend,react:frontend",
                        "--architecture-style",
                        "modular-monolith",
                        "--deployment-style",
                        "single-deployable",
                    ],
                    project_root=project_root,
                ),
                0,
            )

            target_stack = state.read_json("architecture", "target-stack.json")
            self.assertEqual(target_stack["architectureStyle"], "modular-monolith")
            self.assertEqual(target_stack["deploymentStyle"], "single-deployable")

    def test_choose_provider_interactive_uses_prompted_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            source_root = project_root / "fixtures"
            source_root.mkdir()
            (source_root / "login.cfm").write_text("<cfif true></cfif>", encoding="utf-8")

            self.assertEqual(run_cli(["init", str(source_root)], project_root=project_root), 0)
            with patch("sys.stdin.isatty", return_value=True), patch(
                "builtins.input", side_effect=["5"]
            ):
                self.assertEqual(run_cli(["choose-provider"], project_root=project_root), 0)

            migration = ProjectState(project_root).load_migration()
            self.assertEqual(migration["project"]["provider"], "command-json")


if __name__ == "__main__":
    unittest.main()
