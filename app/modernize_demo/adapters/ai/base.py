"""Base interfaces for pluggable AI providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SemanticDerivation:
    """Normalized semantic derivation returned by an AI provider."""

    summary: str
    module_role: str
    business_capabilities: list[dict]
    confidence: int
    field_confidences: dict[str, int]
    provider: str


@dataclass
class GeneratedApplication:
    """Normalized AI-generated application file set."""

    files: dict[str, str]
    provider: str
    notes: list[str]


class AIProvider(Protocol):
    """Contract for semantic derivation providers."""

    name: str

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        """Return a semantic derivation for one fact artifact."""

    def generate_application(self, generation_context: dict) -> GeneratedApplication:
        """Generate application code files from locked modernization artifacts."""
