"""Shared data models for the modernization demo."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


def to_dict(value: Any) -> Any:
    """Convert dataclasses to plain dictionaries recursively."""
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


@dataclass
class TargetStackEntry:
    """A selected target adapter entry."""

    adapter: str
    role: str


@dataclass
class ProjectConfig:
    """Persistent project configuration written during init."""

    project_name: str
    source_path: str
    source_language: str
    target_stack: list[TargetStackEntry]
    provider: str
    trust_level: str
    created_at: str
    target_architecture_profile: dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionArgument:
    """A parsed function argument."""

    name: str
    type: str
    required: bool


@dataclass
class QueryInfo:
    """A parsed query block."""

    name: str
    operation: str
    tables: list[str]
    parameterized: bool
    sql_excerpt: str


@dataclass
class FunctionNode:
    """A parsed function block from ColdFusion."""

    name: str
    access: str
    return_type: str
    arguments: list[FunctionArgument] = field(default_factory=list)
    queries: list[QueryInfo] = field(default_factory=list)
    conditionals: list[str] = field(default_factory=list)
    scope_writes: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    throws: list[str] = field(default_factory=list)
    return_present: bool = False


@dataclass
class AstArtifact:
    """Persisted AST-like representation for a module."""

    module: str
    source_file: str
    source_hash: str
    adapter_version: str
    parse_status: str
    module_type: str
    diagnostics: list[str]
    config_usage: list[str]
    endpoints: list[str]
    ui_evidence: dict[str, Any] = field(default_factory=dict)
    component_extends: str | None = None
    functions: list[FunctionNode] = field(default_factory=list)


@dataclass
class FactArtifact:
    """Deterministic facts extracted from the AST artifact."""

    module: str
    file_path: str
    module_type: str
    reads: list[str]
    writes: list[str]
    tables_touched: list[dict[str, Any]]
    session_usage: list[str]
    config_usage: list[str]
    calls: list[str]
    includes: list[str]
    endpoints: list[dict[str, Any]]
    dependencies: list[str]
    functions: list[dict[str, Any]]
    inference_notes: list[dict[str, Any]]
    ui_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticArtifact:
    """Reviewed semantic understanding for one module."""

    module: str
    file_path: str
    summary: str
    module_role: str
    business_capabilities: list[dict[str, Any]]
    dependencies: list[str]
    data_touch_points: list[str]
    confidence: int
    fields: dict[str, dict[str, Any]]
    review: dict[str, Any]
