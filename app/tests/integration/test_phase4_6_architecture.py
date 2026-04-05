"""Phase 4-6 integration tests: architecture derivation, comparison, and locks."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from modernize import run_cli
from modernize_demo.core.state import ProjectState
from modernize_demo.pipeline.target_architect import _normalize_target_role


class ArchitecturePhaseTests(unittest.TestCase):
    """Exercise source and target architecture phases."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.source_root = self.project_root / "source"
        fixtures_root = Path(__file__).resolve().parents[1] / "fixtures" / "coldfusion"
        shutil.copytree(fixtures_root, self.source_root)
        run_cli(["init", str(self.source_root)], project_root=self.project_root)
        for command in [
            ["discover"],
            ["parse"],
            ["facts"],
            ["extract"],
            ["approve", "semantics", "--all"],
            ["lock", "semantics"],
            ["source-architect"],
            ["approve", "source-architecture"],
            ["lock", "source-architecture"],
            [
                "choose-target-stack",
                "--target-stack",
                "python:backend,react:frontend",
                "--architecture-style",
                "service-oriented",
                "--deployment-style",
                "single-deployable",
            ],
            ["target-architect"],
            ["approve", "target-architecture"],
            ["lock", "target-architecture"],
        ]:
            self.assertEqual(run_cli(command, project_root=self.project_root), 0, msg=command)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_source_and_target_architecture_outputs_exist(self) -> None:
        state = ProjectState(self.project_root)
        source_doc = state.read_text("architecture", "source-architecture.md")
        self.assertIn("```mermaid", source_doc)
        source_review_index = state.read_text("docs", "source-architecture/index.md")
        self.assertIn("Source Architecture Review", source_review_index)
        source_review_module = state.read_text("docs", "source-architecture/modules/UserService.md")
        self.assertIn("## Evidence", source_review_module)
        target_doc = state.read_text("architecture", "target-architecture.md")
        self.assertIn("auth-service", target_doc)
        self.assertIn("Forms:", target_doc)
        self.assertIn("Architectural style:", target_doc)
        self.assertIn("Deployment style:", target_doc)

        source_lock = state.read_json("locked", "source-architecture-lock.json")
        target_lock = state.read_json("locked", "target-architecture-lock.json")
        self.assertEqual(source_lock["lockType"], "source-architecture")
        self.assertEqual(target_lock["lockType"], "target-architecture")

        target_architecture = state.read_json("architecture", "target-architecture.json")
        login_page = next(component for component in target_architecture["uiComponents"] if component["name"] == "LoginPage")
        self.assertGreaterEqual(len(login_page["forms"]), 1)
        self.assertGreaterEqual(len(login_page["forms"][0]["inputs"]), 2)
        self.assertEqual(login_page["forms"][0]["inputs"][0]["name"], "email")

        self.assertEqual(run_cli(["review", "source-architecture"], project_root=self.project_root), 0)

    def test_target_role_normalization_accepts_provider_specific_labels(self) -> None:
        self.assertEqual(
            _normalize_target_role(
                {
                    "module": "UserService",
                    "module_role": "User Management Service",
                    "summary": "Provides authentication and profile management.",
                    "business_capabilities": [],
                },
                {},
                {},
            ),
            "identity-service",
        )
        self.assertEqual(
            _normalize_target_role(
                {
                    "module": "OrderService",
                    "module_role": "Order Management Service",
                    "summary": "Creates and cancels customer orders.",
                    "business_capabilities": [],
                },
                {},
                {},
            ),
            "order-service",
        )
        self.assertEqual(
            _normalize_target_role(
                {
                    "module": "login",
                    "module_role": "User Authentication Handler",
                    "summary": "Renders the login form and processes sign-in requests.",
                    "business_capabilities": [],
                },
                {},
                {},
            ),
            "request-entrypoint",
        )


if __name__ == "__main__":
    unittest.main()
