from __future__ import annotations

import logging

import click

from data.config import get_setting, set_setting
from util.config import get_db_path
from util.crypto import encrypt_value

logger = logging.getLogger(__name__)

PROVIDER_MODEL_MAP: dict[str, list[str]] = {
    "anthropic": [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-latest",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
    ],
    "google": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "llama-4-scout-17b-16e-instruct",
    ],
    "openrouter": [
        "deepseek/deepseek-v4-flash:free",
        "moonshotai/kimi-k2.6:free",
    ],
}

PROVIDER_API_KEY_NAMES: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google AI Studio",
    "groq": "Groq",
    "openrouter": "OpenRouter",
}

RECOMMENDED_FREE: list[tuple[str, str]] = [
    ("google", "gemini-2.5-flash"),
    ("groq", "llama-4-scout-17b-16e-instruct"),
    ("openrouter", "deepseek/deepseek-v4-flash:free"),
    ("openrouter", "moonshotai/kimi-k2.6:free"),
]


def _show_config(db_path) -> None:
    existing_model = get_setting(db_path, "model")
    existing_key_providers = []
    for provider in PROVIDER_API_KEY_NAMES:
        if get_setting(db_path, f"api_key_{provider}"):
            existing_key_providers.append(PROVIDER_API_KEY_NAMES[provider])

    if existing_model or existing_key_providers:
        click.echo()
        click.echo("Current configuration:")
        if existing_model:
            click.echo(f"  Model: {existing_model}")
        if existing_key_providers:
            click.echo(f"  API keys stored: {', '.join(existing_key_providers)}")
        click.echo()


def _pick_provider() -> str:
    click.echo()
    click.echo("Select an LLM provider:")
    click.echo("─" * 40)
    providers = list(PROVIDER_MODEL_MAP.keys())
    for i, provider in enumerate(providers, 1):
        label = PROVIDER_API_KEY_NAMES[provider]
        click.echo(f"  {i}. {label} ({provider})")
    click.echo()
    choice = click.prompt(
        "Enter number",
        type=click.IntRange(1, len(providers)),
        show_choices=False,
    )
    return providers[choice - 1]


def _pick_model(provider: str) -> str:
    models = PROVIDER_MODEL_MAP[provider]
    click.echo()
    click.echo(f"Select a model for {PROVIDER_API_KEY_NAMES[provider]}:")
    click.echo("─" * 40)
    for i, model in enumerate(models, 1):
        # Highlight recommended free models
        is_free = (provider, model) in RECOMMENDED_FREE
        suffix = " ✨ Free tier" if is_free else ""
        click.echo(f"  {i}. {model}{suffix}")
    click.echo()
    choice = click.prompt(
        "Enter number",
        type=click.IntRange(1, len(models)),
        show_choices=False,
    )
    return models[choice - 1]


def _enter_api_key(provider: str) -> str | None:
    click.echo()
    label = PROVIDER_API_KEY_NAMES[provider]
    click.echo(
        f"Enter your {label} API key.\n"
        f"  It will be encrypted and stored in the local database.\n"
    )
    api_key = click.prompt("API key", hide_input=True, default="", show_default=False)
    if not api_key.strip():
        click.echo("  (skipped — using env var or existing key at runtime)")
        return None
    return api_key.strip()


@click.command()
@click.option("--show", is_flag=True, help="Show current configuration without changing")
def setup(show: bool) -> None:
    """Interactively configure LLM model and API key.

    Settings are stored encrypted in the local database.
    """
    db_path = get_db_path()

    if show:
        _show_config(db_path)
        return

    click.echo()
    click.echo("╭─ AutoFi Setup ───────────────────────────────╮")
    click.echo("│                                                │")
    click.echo("│  Configure your LLM provider and API key.      │")
    click.echo("│  Settings are stored encrypted in the database.│")
    click.echo("│                                                │")
    click.echo("╰────────────────────────────────────────────────╯")

    _show_config(db_path)

    # Step 1: Pick provider
    provider = _pick_provider()

    # Step 2: Pick model
    model_name = _pick_model(provider)
    full_model = f"{provider}:{model_name}"

    # Step 3: Enter API key
    api_key = _enter_api_key(provider)

    # Step 4: Confirm
    click.echo()
    click.echo("─" * 40)
    click.echo("Summary:")
    click.echo(f"  Provider: {PROVIDER_API_KEY_NAMES[provider]} ({provider})")
    click.echo(f"  Model:    {full_model}")
    click.echo(f"  API key:  {'✓ set (will be encrypted)' if api_key else '✗ not provided (will use env var)'}")
    click.echo()
    if not click.confirm("Save this configuration?", default=True):
        click.echo("Aborted.")
        return

    # Step 5: Save
    try:
        set_setting(db_path, "model", full_model)
        if api_key:
            encrypted = encrypt_value(api_key)
            set_setting(db_path, f"api_key_{provider}", encrypted)
        click.echo()
        click.echo("✓ Configuration saved successfully!")
        click.echo()
        click.echo("You can now use:")
        click.echo('  autofi chat "Show me my transactions"')
        click.echo()
        click.echo("To reconfigure later, re-run:")
        click.echo("  autofi setup")
    except Exception as exc:
        logger.error("Setup failed: %s", exc)
        click.echo(f"Error saving configuration: {exc}", err=True)
        raise click.Abort()
