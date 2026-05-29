from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic_ai import models as _models

from pydantic_ai.providers import infer_provider as _infer_provider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "anthropic:claude-sonnet-4-20250514"

PROVIDER_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google-gla": "GOOGLE_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# Mapping of provider name to (model_class_import_path, provider_class_import_path)
# and a factory callable that creates the provider given an API key
_PROVIDER_FACTORIES: dict[str, Any] = {}


def _build_provider_factories():
    global _PROVIDER_FACTORIES
    if _PROVIDER_FACTORIES:
        return

    from pydantic_ai.providers.anthropic import AnthropicProvider
    from pydantic_ai.providers.google import GoogleProvider
    from pydantic_ai.providers.groq import GroqProvider
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    _PROVIDER_FACTORIES = {
        "anthropic": lambda api_key: AnthropicProvider(api_key=api_key),
        "openai": lambda api_key: OpenAIProvider(api_key=api_key),
        "google-gla": lambda api_key: GoogleProvider(api_key=api_key),
        "google": lambda api_key: GoogleProvider(api_key=api_key),
        "groq": lambda api_key: GroqProvider(api_key=api_key),
        "openrouter": lambda api_key: OpenRouterProvider(
            api_key=api_key,
            openai_client=AsyncOpenAI(api_key=api_key, max_retries=0),  # pyright: ignore[reportArgumentType]
        ),
    }


def _get_db_path() -> Path | None:
    from util.config import get_db_path as _get_db_path

    try:
        return _get_db_path()
    except Exception:
        return None


def _read_db_setting(key: str) -> str | None:
    db_path = _get_db_path()
    if db_path is None:
        return None
    from data.config import get_setting as _get_setting

    try:
        return _get_setting(db_path, key)
    except Exception:
        return None


def get_model_string() -> str:
    db_model = _read_db_setting("model")
    if db_model:
        return db_model
    return os.environ.get("AUTOFI_LLM_MODEL", DEFAULT_MODEL)


def get_model_for_agent(agent_name: str) -> str:
    env_var = f"AUTOFI_{agent_name.upper()}_MODEL"
    model = os.environ.get(env_var)
    if model:
        return model
    return get_model_string()


def get_provider_from_model(model: str) -> str:
    return model.split(":")[0]


def _get_model_name_from_model(model_str: str) -> str:
    """Extract the model name after the provider prefix."""
    parts = model_str.split(":")
    return ":".join(parts[1:])


def resolve_api_key(provider: str) -> str | None:
    # Try DB first
    encrypted = _read_db_setting(f"api_key_{provider}")
    if encrypted:
        from util.crypto import decrypt_value as _decrypt_value

        try:
            return _decrypt_value(encrypted)
        except Exception as exc:
            logger.warning("Failed to decrypt API key for '%s': %s", provider, exc)

    # Fall back to env var
    env_var = PROVIDER_ENV_VARS.get(provider)
    if env_var is None:
        logger.warning("Unknown LLM provider '%s'", provider)
        return None
    return os.environ.get(env_var)


def create_agent_model(agent_name: str) -> _models.Model | str:
    """Create a Model instance for the given agent, injecting API key from DB or env.

    Returns a Model instance when an API key is available (DB or env).
    Returns the model string when no API key is set anywhere — the Agent
    constructor with ``defer_model_check=True`` will handle lazy resolution.
    """
    model_str = get_model_for_agent(agent_name)
    _build_provider_factories()

    provider = get_provider_from_model(model_str)
    api_key = resolve_api_key(provider)

    if api_key is None:
        # Check if the standard env var is set — if so, let pydantic-ai resolve
        env_var = PROVIDER_ENV_VARS.get(provider)
        if env_var and os.environ.get(env_var):
            return _models.infer_model(model_str)
        # No key at all — return string for deferred resolution
        return model_str

    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        logger.warning(
            "No custom provider factory for '%s', falling back to env-var resolution",
            provider,
        )
        return _models.infer_model(model_str)

    custom_provider = factory(api_key)

    # Build a provider_factory that returns our custom provider for this provider,
    # and falls back to the default for any other (e.g. sub-agent delegation)
    def provider_factory(name: str) -> Any:
        if name == provider:
            return custom_provider
        return _infer_provider(name)

    return _models.infer_model(model_str, provider_factory=provider_factory)
