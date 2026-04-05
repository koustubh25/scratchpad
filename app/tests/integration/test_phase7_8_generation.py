"""Phase 7-8 integration tests: generation, smoke run, verification, invalidation."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from modernize import run_cli
from modernize_demo.core.state import ProjectState


class GenerationVerificationTests(unittest.TestCase):
    """Exercise generation, runtime smoke checks, and stale lock detection."""

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
            ["choose-target-stack", "--target-stack", "python:backend,react:frontend"],
            ["target-architect"],
            ["approve", "target-architecture"],
            ["lock", "target-architecture"],
            ["generate", "demo-app"],
            ["verify", "demo-app"],
        ]:
            self.assertEqual(run_cli(command, project_root=self.project_root), 0, msg=command)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generated_app_runs_and_verification_artifact_exists(self) -> None:
        state = ProjectState(self.project_root)
        service_root = state.path_for("services", "demo-app")
        self.assertTrue((service_root / "backend" / "server.py").exists())
        self.assertTrue((service_root / "frontend" / "index.html").exists())
        app_js = (service_root / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn("primaryPage?.headings?.[0]", app_js)
        self.assertIn("input.label ||", app_js)
        self.assertIn("buildNotice", app_js)
        self.assertNotIn("API Contracts", app_js)

        port = _find_open_port()
        process = subprocess.Popen(
            ["python3", str(service_root / "backend" / "server.py")],
            cwd=service_root / "backend",
            env={**os.environ, "MODERNIZE_DEMO_PORT": str(port)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_server(port)
            home = urlopen(f"http://127.0.0.1:{port}/").read().decode("utf-8")
            self.assertIn('id="root"', home)
            self.assertIn("/app.js", home)

            meta_payload = json.loads(urlopen(f"http://127.0.0.1:{port}/api/meta").read().decode("utf-8"))
            self.assertGreaterEqual(len(meta_payload["contracts"]), 1)
            self.assertIn("behaviorCatalog", json.loads((service_root / "backend" / "generated_config.json").read_text(encoding="utf-8")))

            contract = meta_payload["contracts"][0]
            path = contract["path"].replace("{user_id}", "1").replace("{id}", "1")
            if contract["method"] == "GET":
                response_payload = json.loads(urlopen(f"http://127.0.0.1:{port}{path}").read().decode("utf-8"))
                self.assertEqual(response_payload["service"], contract["service"])
            else:
                payload = {"demo": True}
                if path == "/login":
                    payload = {"email": "demo@example.com", "password": "password123"}
                request = Request(
                    f"http://127.0.0.1:{port}{path}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method=contract["method"],
                )
                response_payload = json.loads(urlopen(request).read().decode("utf-8"))
                self.assertEqual(response_payload["service"], contract["service"])
        finally:
            process.terminate()
            process.communicate(timeout=5)

        report = state.read_json("recordings/demo-app", "verification-report.json")
        self.assertEqual(report["verdict"], "PASS")

    def test_status_marks_semantic_lock_stale_after_source_changes_and_discovery_reruns(self) -> None:
        source_file = self.source_root / "login.cfm"
        source_file.write_text(source_file.read_text(encoding="utf-8") + "\n<!-- stale check -->\n", encoding="utf-8")
        self.assertEqual(run_cli(["discover"], project_root=self.project_root), 0)
        state = ProjectState(self.project_root)
        semantic_lock = state.read_json("locked", "semantic-lock.json")
        self.assertIsNotNone(semantic_lock)
        status_payload = json.loads(_run_cli_capture(["status"], self.project_root))
        self.assertEqual(status_payload["locks"]["semantic"]["stale"], True)


def _find_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return handle.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/health") as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise TimeoutError("server did not start")


def _run_cli_capture(argv: list[str], project_root: Path) -> str:
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "MODERNIZE_PROJECT_ROOT": str(project_root)}
    process = subprocess.run(
        ["python3", "modernize.py", *argv],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return process.stdout


if __name__ == "__main__":
    unittest.main()
