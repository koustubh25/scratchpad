"""Phase 2-3 integration tests: discovery through semantic lock."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from modernize import run_cli
from modernize_demo.core.state import ProjectState


class PipelinePhaseTwoThreeTests(unittest.TestCase):
    """Exercise the demo CLI through semantic lock."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.source_root = self.project_root / "source"
        fixtures_root = Path(__file__).resolve().parents[1] / "fixtures" / "coldfusion"
        shutil.copytree(fixtures_root, self.source_root)
        run_cli(
            [
                "init",
                str(self.source_root),
            ],
            project_root=self.project_root,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_discover_parse_facts_extract_and_lock(self) -> None:
        commands = [
            ["discover"],
            ["parse"],
            ["facts"],
            ["extract"],
            ["correct", "semantics", "login", "--field", "summary", "--value", "Login handles sign-in and delegates identity checks."],
            ["approve", "semantics", "--all"],
            ["lock", "semantics"],
        ]
        for command in commands:
            self.assertEqual(run_cli(command, project_root=self.project_root), 0, msg=command)

        state = ProjectState(self.project_root)
        discovery = state.read_json("discovery", "source-discovery.json")
        self.assertEqual(len(discovery["discoveredSourceFiles"]), 3)

        user_ast = state.read_json("ast", "UserService.ast.json")
        self.assertEqual(user_ast["module_type"], "component")
        self.assertGreaterEqual(len(user_ast["functions"]), 1)

        user_facts = state.read_json("facts", "UserService.facts.json")
        self.assertIn("users", user_facts["reads"])
        self.assertIn("session.userId", user_facts["session_usage"])

        review_index = state.read_text("docs", "semantic-review/index.md")
        self.assertIn("Semantic Review Index", review_index)
        self.assertIn("OrderService", review_index)
        login_review = state.read_text("docs", "semantic-review/modules/login.md")
        self.assertIn("Semantic Review: login", login_review)
        review_payload = run_cli(["review", "semantics"], project_root=self.project_root)
        self.assertEqual(review_payload, 0)

        order_semantics = state.read_json("semantics", "OrderService.semantic.json")
        self.assertEqual(order_semantics["review"]["approved"], True)
        self.assertIn("order-service", order_semantics["module_role"])
        login_semantics = state.read_json("semantics", "login.semantic.json")
        self.assertEqual(login_semantics["summary"], "Login handles sign-in and delegates identity checks.")
        self.assertEqual(login_semantics["fields"]["summary"]["source"], "human")

        semantic_lock = state.read_json("locked", "semantic-lock.json")
        self.assertEqual(sorted(semantic_lock["modules"]), ["OrderService", "UserService", "login"])


if __name__ == "__main__":
    unittest.main()
