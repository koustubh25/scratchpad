"""Native OpenAI semantic provider."""

from __future__ import annotations

import os

from .base import GeneratedApplication, SemanticDerivation
from .prompting import (
    GENERATION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_generation_prompt,
    build_semantic_prompt,
    parse_json_payload,
)


class OpenAIProvider:
    """Use the OpenAI Python SDK for semantic derivation."""

    name = "openai"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.environ.get("MODERNIZE_OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("openai provider requires OPENAI_API_KEY")

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for provider 'openai'") from exc

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=build_semantic_prompt(facts),
        )
        payload = parse_json_payload(response.output_text)
        return _to_derivation(payload, self.name)

    def generate_application(self, generation_context: dict) -> GeneratedApplication:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for provider 'openai'") from exc

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            instructions=GENERATION_SYSTEM_PROMPT,
            input=build_generation_prompt(generation_context),
        )
        payload = parse_json_payload(response.output_text)
        return _to_generated_application(payload, self.name)


def _to_derivation(payload: dict, provider_name: str) -> SemanticDerivation:
    return SemanticDerivation(
        summary=payload["summary"],
        module_role=payload["moduleRole"],
        business_capabilities=[
            {
                "function": item["function"],
                "description": item["description"],
                "source": "ai",
                "confidence": int(item["confidence"]),
            }
            for item in payload["businessCapabilities"]
        ],
        confidence=int(payload["confidence"]),
        field_confidences={
            "summary": int(payload["fieldConfidences"]["summary"]),
            "moduleRole": int(payload["fieldConfidences"]["moduleRole"]),
            "businessCapabilities": int(payload["fieldConfidences"]["businessCapabilities"]),
        },
        provider=provider_name,
    )


def _to_generated_application(payload: dict, provider_name: str) -> GeneratedApplication:
    files = {}
    for item in payload["files"]:
        files[item["path"]] = item["content"]
    return GeneratedApplication(
        files=files,
        provider=provider_name,
        notes=list(payload.get("notes", [])),
    )
