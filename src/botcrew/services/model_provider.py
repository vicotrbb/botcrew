"""Agno model provider factory.

Maps (provider, model_name) tuples to configured Agno model instances.
Supports OpenAI, Anthropic, Ollama natively, and Z.ai/GLM via OpenAI-compatible mode.
"""

from __future__ import annotations

from typing import Any

from agno.models.anthropic import Claude
from agno.models.ollama import Ollama
from agno.models.openai import OpenAIResponses

PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
    "openai": {
        "class": OpenAIResponses,
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "class": Claude,
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
    },
    "ollama": {
        "class": Ollama,
        "env_key": None,
        "default_model": "llama3.2",
    },
    "glm": {
        "class": OpenAIResponses,
        "env_key": "GLM_API_KEY",
        "default_model": "glm-5",
        "base_url": "https://api.z.ai/api/paas/v4/",
    },
}

SUPPORTED_PROVIDERS: list[str] = sorted(PROVIDER_REGISTRY.keys())


def create_model(
    provider: str,
    model_name: str,
    secrets: dict[str, str],
) -> OpenAIResponses | Claude | Ollama:
    """Create an Agno model instance for the given provider and model.

    Each Agno model class has different constructor parameters:
    - OpenAIResponses: id, api_key, optionally base_url
    - Claude: id, api_key
    - Ollama: id, host (no api_key)

    Args:
        provider: One of 'openai', 'anthropic', 'ollama', 'glm'.
        model_name: The model identifier (e.g. 'gpt-4o', 'claude-sonnet-4-5').
        secrets: Dict of system-wide API keys from the secrets table.

    Returns:
        Configured Agno model instance.

    Raises:
        ValueError: If provider is unknown or required API key is missing.
    """
    config = PROVIDER_REGISTRY.get(provider)
    if not config:
        raise ValueError(
            f"Unknown provider: '{provider}'. Supported providers: {SUPPORTED_PROVIDERS}"
        )

    kwargs: dict[str, Any] = {"id": model_name}

    env_key = config.get("env_key")
    if env_key:
        api_key = secrets.get(env_key)
        if not api_key:
            raise ValueError(
                f"API key '{env_key}' not configured. Add it via the secrets API."
            )
        kwargs["api_key"] = api_key

    # Inject base_url for OpenAI-compatible providers (e.g. Z.ai/GLM)
    if "base_url" in config:
        kwargs["base_url"] = config["base_url"]

    # Inject Ollama host if configured (do NOT pass api_key to Ollama)
    if provider == "ollama":
        ollama_host = secrets.get("OLLAMA_HOST", "http://localhost:11434")
        kwargs["host"] = ollama_host

    return config["class"](**kwargs)


def validate_provider_configured(
    provider: str,
    secrets: dict[str, str],
) -> bool:
    """Check if the required API key exists for a provider.

    Used at agent creation/edit time to reject providers whose
    credentials have not been configured.

    Args:
        provider: Provider name to validate.
        secrets: Dict of system-wide API keys.

    Returns:
        True if the provider is known and its required credentials are present.
    """
    config = PROVIDER_REGISTRY.get(provider)
    if not config:
        return False
    env_key = config.get("env_key")
    if env_key is None:
        # Ollama doesn't need an API key
        return True
    return env_key in secrets and bool(secrets[env_key])
