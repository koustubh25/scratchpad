"""Project state and artifact helpers for the modernization demo."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ProjectConfig, TargetStackEntry


class ProjectState:
    """Manage the .modernize state directory and migration metadata."""

    SUBDIRECTORIES = [
        "discovery",
        "ast",
        "facts",
        "semantics",
        "architecture",
        "docs",
        "corrections",
        "locked",
        "services",
        "recordings",
        "audit",
    ]

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.modernize_dir = self.project_root / ".modernize"
        self.migration_file = self.modernize_dir / "migration.json"

    @property
    def is_initialized(self) -> bool:
        return self.migration_file.exists()

    def now_iso(self) -> str:
        """Return a timezone-aware timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def path_for(self, subdir: str, filename: str) -> Path:
        """Return the full path for an artifact."""
        return self.modernize_dir / subdir / filename

    def init(self, source_path: str, target_stack: list[dict[str, str]], provider: str, trust_level: str) -> None:
        """Initialize the project and write baseline state."""
        self.modernize_dir.mkdir(parents=True, exist_ok=True)
        for subdir in self.SUBDIRECTORIES:
            (self.modernize_dir / subdir).mkdir(parents=True, exist_ok=True)

        config = ProjectConfig(
            project_name=Path(source_path).resolve().name,
            source_path=str(Path(source_path).resolve()),
            source_language="coldfusion",
            target_stack=[TargetStackEntry(**entry) for entry in target_stack],
            provider=provider,
            trust_level=trust_level,
            created_at=self.now_iso(),
        )
        migration = {
            "project": self._normalize(config),
            "pipeline": {
                "currentStep": "initialized",
                "steps": {
                    "discover": {"status": "pending"},
                    "parse": {"status": "pending"},
                    "facts": {"status": "pending"},
                    "extract": {"status": "pending"},
                    "review_semantics": {"status": "pending"},
                    "lock_semantics": {"status": "pending"},
                    "source_architect": {"status": "pending"},
                    "review_source_architecture": {"status": "pending"},
                    "lock_source_architecture": {"status": "pending"},
                    "choose_target_stack": {"status": "pending"},
                    "target_architect": {"status": "pending"},
                    "review_target_architecture": {"status": "pending"},
                    "lock_target_architecture": {"status": "pending"},
                    "generate": {"status": "pending"},
                    "verify": {"status": "pending"},
                },
            },
        }
        self.write_json_root("migration.json", migration)

    def load_migration(self) -> dict[str, Any]:
        """Load the migration state."""
        return self._read_json(self.migration_file)

    def save_migration(self, payload: dict[str, Any]) -> None:
        """Persist the migration state."""
        self._write_json(self.migration_file, payload)

    def update_project_config(self, **fields: Any) -> dict[str, Any]:
        """Update project-level configuration fields."""
        migration = self.load_migration()
        migration["project"].update(self._normalize(fields))
        self.save_migration(migration)
        return migration["project"]

    def update_step(self, step: str, status: str, **fields: Any) -> None:
        """Update a pipeline step in migration state."""
        migration = self.load_migration()
        migration["pipeline"]["steps"].setdefault(step, {})
        migration["pipeline"]["steps"][step]["status"] = status
        migration["pipeline"]["steps"][step].update(self._normalize(fields))
        migration["pipeline"]["currentStep"] = step
        self.save_migration(migration)

    def get_step_status(self, step: str) -> str:
        """Return the current status of one pipeline step."""
        if not self.is_initialized:
            return "missing"
        return self.load_migration()["pipeline"]["steps"].get(step, {}).get("status", "missing")

    def write_json_root(self, filename: str, data: Any) -> Path:
        """Write a JSON file under .modernize directly."""
        path = self.modernize_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(path, data)
        return path

    def write_json(self, subdir: str, filename: str, data: Any) -> Path:
        """Write a JSON artifact."""
        path = self.path_for(subdir, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(path, data)
        return path

    def read_json(self, subdir: str, filename: str) -> Any | None:
        """Read a JSON artifact when it exists."""
        path = self.path_for(subdir, filename)
        if not path.exists():
            return None
        return self._read_json(path)

    def write_text(self, subdir: str, filename: str, content: str) -> Path:
        """Write a text artifact."""
        path = self.path_for(subdir, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_text(self, subdir: str, filename: str) -> str | None:
        """Read a text artifact when it exists."""
        path = self.path_for(subdir, filename)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_files(self, subdir: str, suffix: str = "") -> list[Path]:
        """List files in a state subdirectory with an optional suffix filter."""
        directory = self.modernize_dir / subdir
        if not directory.exists():
            return []
        files = [path for path in directory.rglob("*") if path.is_file()]
        if suffix:
            files = [path for path in files if path.name.endswith(suffix)]
        return sorted(files)

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(
            json.dumps(self._normalize(data), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _read_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _normalize(self, data: Any) -> Any:
        if is_dataclass(data):
            return asdict(data)
        if isinstance(data, dict):
            return {key: self._normalize(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._normalize(value) for value in data]
        return data
