"""Shared prompting and JSON parsing helpers for native AI providers."""

from __future__ import annotations

import json


SYSTEM_PROMPT = """You are an architecture modernization assistant.
You receive deterministic fact artifacts extracted from legacy code.
Return only valid JSON matching the requested schema.
Do not include markdown fences or commentary.
Use a confidence scale from 0 to 100.
Keep businessCapabilities concise and factual."""

GENERATION_SYSTEM_PROMPT = """You are an architecture modernization code generator.
You receive locked modernization artifacts and target adapter conventions.
Generate only the requested target code files.
Return only valid JSON matching the requested schema.
Do not include markdown fences or commentary.
Preserve source-backed behavior where the artifacts clearly support it.
Prefer concrete, runnable code over placeholders.
Do not invent source pages or flows that are not supported by the artifacts."""


def build_semantic_prompt(facts: dict) -> str:
    """Build the user prompt for semantic derivation."""
    return json.dumps(
        {
            "task": "derive_semantics",
            "instructions": [
                "Infer a short semantic summary for the module.",
                "Infer the best module role based on facts.",
                "Infer business capabilities from functions and dependencies.",
                "Return strict JSON only.",
            ],
            "facts": facts,
            "outputSchema": {
                "summary": "string",
                "moduleRole": "string",
                "businessCapabilities": [
                    {
                        "function": "string",
                        "description": "string",
                        "confidence": "0..100 int",
                    }
                ],
                "confidence": "0..100 int",
                "fieldConfidences": {
                    "summary": "0..100 int",
                    "moduleRole": "0..100 int",
                    "businessCapabilities": "0..100 int",
                },
            },
        },
        indent=2,
        sort_keys=True,
    )


def build_generation_prompt(generation_context: dict) -> str:
    """Build the user prompt for AI-driven code generation."""
    return json.dumps(
        {
            "task": "generate_application_files",
            "instructions": [
                "Use the locked artifacts as the primary source of truth.",
                "Generate backend and frontend code files for the requested stack.",
                "Preserve source-backed behavior where the evidence is strong.",
                "Use target adapter conventions for file shape and runtime style.",
                "Return strict JSON only.",
            ],
            "generationContext": generation_context,
            "outputSchema": {
                "files": [
                    {
                        "path": "frontend/app.js | frontend/styles.css | backend/app_logic.py",
                        "content": "string file contents",
                    }
                ],
                "notes": ["string"],
            },
        },
        indent=2,
        sort_keys=True,
    )


def parse_json_payload(raw_text: str) -> dict:
    """Parse model text into JSON, tolerating fenced JSON blocks."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)
