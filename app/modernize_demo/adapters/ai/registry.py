"""Provider registry and loader for semantic AI adapters."""

from __future__ import annotations

import importlib

from ...core.state import ProjectState
from .anthropic_provider import AnthropicProvider
from .base import AIProvider
from .command_provider import CommandJSONProvider
from .demo_provider import DemoAIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


def load_provider(state: ProjectState) -> AIProvider:
    """Load the provider selected during init."""
    migration = state.load_migration()
    provider_spec = migration["project"]["provider"]

    if provider_spec == "demo-ai":
        return DemoAIProvider()
    if provider_spec == "openai":
        return OpenAIProvider()
    if provider_spec == "anthropic":
        return AnthropicProvider()
    if provider_spec == "gemini":
        return GeminiProvider()
    if provider_spec == "command-json":
        return CommandJSONProvider.from_environment()
    if provider_spec.startswith("python:"):
        return _load_python_provider(provider_spec)

    raise RuntimeError(
        "Unsupported provider. Use 'demo-ai', 'openai', 'anthropic', 'gemini', "
        "'command-json', or 'python:<module>:<symbol>'."
    )


def _load_python_provider(provider_spec: str) -> AIProvider:
    try:
        _, module_name, symbol_name = provider_spec.split(":", 2)
    except ValueError as exc:
        raise RuntimeError(
            "python provider spec must be formatted as python:<module>:<symbol>"
        ) from exc
    module = importlib.import_module(module_name)
    symbol = getattr(module, symbol_name)
    provider = symbol() if callable(symbol) else symbol
    if not hasattr(provider, "derive_semantics"):
        raise RuntimeError("Loaded python provider does not implement derive_semantics(facts)")
    return provider
