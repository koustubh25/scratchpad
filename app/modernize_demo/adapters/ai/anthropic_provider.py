"""Native Anthropic semantic provider."""

from __future__ import annotations

import os

from .base import GeneratedApplication, SemanticDerivation
from .openai_provider import _to_derivation, _to_generated_application
from .prompting import (
    GENERATION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_generation_prompt,
    build_semantic_prompt,
    parse_json_payload,
)


class AnthropicProvider:
    """Use the Anthropic Python SDK for semantic derivation."""

    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.environ.get("MODERNIZE_ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("anthropic provider requires ANTHROPIC_API_KEY")

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package is required for provider 'anthropic'") from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_semantic_prompt(facts)}],
        )
        text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        payload = parse_json_payload("\n".join(text_blocks))
        return _to_derivation(payload, self.name)

    def generate_application(self, generation_context: dict) -> GeneratedApplication:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package is required for provider 'anthropic'") from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=GENERATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_generation_prompt(generation_context)}],
        )
        text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        payload = parse_json_payload("\n".join(text_blocks))
        return _to_generated_application(payload, self.name)
