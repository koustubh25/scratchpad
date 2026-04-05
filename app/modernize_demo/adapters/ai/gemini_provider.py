"""Native Google Gemini semantic provider."""

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


class GeminiProvider:
    """Use the Google GenAI SDK for semantic derivation."""

    name = "gemini"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.environ.get("MODERNIZE_GEMINI_MODEL", "gemini-2.5-flash")
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.use_vertexai = _env_truthy(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))
        self.project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai package is required for provider 'gemini'") from exc

        client = self._build_client(genai)
        response = client.models.generate_content(
            model=self.model,
            contents=f"{SYSTEM_PROMPT}\n\n{build_semantic_prompt(facts)}",
        )
        payload = parse_json_payload(response.text)
        return _to_derivation(payload, self.name)

    def generate_application(self, generation_context: dict) -> GeneratedApplication:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai package is required for provider 'gemini'") from exc

        client = self._build_client(genai)
        response = client.models.generate_content(
            model=self.model,
            contents=f"{GENERATION_SYSTEM_PROMPT}\n\n{build_generation_prompt(generation_context)}",
        )
        payload = parse_json_payload(response.text)
        return _to_generated_application(payload, self.name)

    def _build_client(self, genai_module):
        api_key = self.google_api_key or self.api_key
        if api_key and not self.use_vertexai:
            return genai_module.Client(api_key=api_key)

        if self.use_vertexai or self.project or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            if not self.project:
                raise RuntimeError(
                    "gemini provider using Vertex AI / Application Default Credentials requires "
                    "GOOGLE_CLOUD_PROJECT to be set"
                )
            return genai_module.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
            )

        raise RuntimeError(
            "gemini provider requires either GEMINI_API_KEY / GOOGLE_API_KEY, or Vertex AI "
            "Application Default Credentials with GOOGLE_CLOUD_PROJECT "
            "(and optionally GOOGLE_CLOUD_LOCATION / GOOGLE_GENAI_USE_VERTEXAI=true)."
        )


def _env_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
