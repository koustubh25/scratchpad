"""State management for .modernize/ directory."""

import json
import os
from pathlib import Path
from datetime import datetime


class ProjectState:
    """Manages the .modernize/ directory and migration.json state."""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.modernize_dir = self.project_path / ".modernize"
        self.migration_file = self.modernize_dir / "migration.json"

    @property
    def is_initialized(self) -> bool:
        return self.migration_file.exists()

    def init(self, source_path: str, target_stack: list[dict], provider: str = "claude",
             trust_level: str = "standard"):
        """Initialize .modernize/ directory structure."""
        dirs = [
            "ast", "semantics", "docs", "corrections",
            "locked", "architecture", "services", "recordings", "audit"
        ]
        for d in dirs:
            (self.modernize_dir / d).mkdir(parents=True, exist_ok=True)

        migration = {
            "project": os.path.basename(source_path),
            "source": {
                "language": "coldfusion",
                "path": source_path,
                "detectedAt": datetime.now().isoformat()
            },
            "targetStack": target_stack,
            "provider": provider,
            "trustLevel": trust_level,
            "pipeline": {
                "currentStep": "initialized",
                "steps": {
                    "parse": {"status": "pending"},
                    "extract": {"status": "pending"},
                    "document": {"status": "pending"},
                    "review": {"status": "pending", "modules": {}},
                    "lock_semantics": {"status": "pending"},
                    "architect": {"status": "pending"},
                    "lock_architecture": {"status": "pending"},
                    "generate": {"status": "pending", "services": {}},
                    "verify": {"status": "pending", "services": {}}
                }
            },
            "serviceGroups": [],
            "createdAt": datetime.now().isoformat()
        }
        self._write_json(self.migration_file, migration)

    def load(self) -> dict:
        return self._read_json(self.migration_file)

    def save(self, state: dict):
        self._write_json(self.migration_file, state)

    def update_step(self, step: str, status: str, **extra):
        state = self.load()
        state["pipeline"]["steps"][step]["status"] = status
        for k, v in extra.items():
            state["pipeline"]["steps"][step][k] = v
        if status == "completed":
            state["pipeline"]["currentStep"] = step
        self.save(state)

    def get_step_status(self, step: str) -> str:
        state = self.load()
        return state["pipeline"]["steps"].get(step, {}).get("status", "unknown")

    def write_artifact(self, subdir: str, filename: str, data, as_json: bool = True):
        path = self.modernize_dir / subdir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        if as_json:
            self._write_json(path, data)
        else:
            path.write_text(data, encoding="utf-8")
        return path

    def read_artifact(self, subdir: str, filename: str, as_json: bool = True):
        path = self.modernize_dir / subdir / filename
        if not path.exists():
            return None
        if as_json:
            return self._read_json(path)
        return path.read_text(encoding="utf-8")

    def list_artifacts(self, subdir: str, suffix: str = ".json") -> list[str]:
        d = self.modernize_dir / subdir
        if not d.exists():
            return []
        return [f.name for f in d.iterdir() if f.suffix == suffix]

    def _write_json(self, path: Path, data: dict):
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
