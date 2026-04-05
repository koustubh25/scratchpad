"""Rendering helpers for deterministic markdown documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def build_environment(template_dir: Path) -> Environment:
    """Build a strict Jinja environment for deterministic rendering."""
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def render_template(template_dir: Path, template_name: str, **context: Any) -> str:
    """Render a template with strict failure on missing fields."""
    env = build_environment(template_dir)
    template = env.get_template(template_name)
    return template.render(**context)

