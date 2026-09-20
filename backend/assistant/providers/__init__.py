"""
Provider registry.

Adding a backend means writing one module and listing it here; nothing
above this package changes.
"""

import os

from backend.assistant.providers.base import (
    ChatResult,
    NotConfigured,
    Provider,
    ProviderError,
)
from backend.assistant.providers.gemini import GeminiProvider
from backend.assistant.providers.local import LocalProvider

#: Tried in order when MATHNOVA_AI_PROVIDER is "auto".
REGISTRY = {
    GeminiProvider.name: GeminiProvider,
    LocalProvider.name: LocalProvider,
}

PREFERENCE = (GeminiProvider, LocalProvider)


def configured_name():
    return os.getenv("MATHNOVA_AI_PROVIDER", "auto").strip().lower() or "auto"


def available():
    """Every provider that could serve a request right now."""

    return [cls for cls in PREFERENCE if cls.is_configured()]


def resolve():
    """
    Pick a provider.

    An explicit MATHNOVA_AI_PROVIDER is honoured even when unconfigured,
    so the resulting error names the backend the operator actually chose
    rather than silently falling back to another one.
    """

    choice = configured_name()

    if choice != "auto":
        cls = REGISTRY.get(choice)

        if cls is None:
            raise NotConfigured(
                f"Unknown AI provider '{choice}'. "
                f"Choose one of: {', '.join(sorted(REGISTRY))}, or 'auto'."
            )

        if not cls.is_configured():
            raise NotConfigured(
                f"The '{cls.name}' provider is selected but not ready. "
                + cls.setup_hint()
            )

        return cls()

    for cls in PREFERENCE:
        if cls.is_configured():
            return cls()

    raise NotConfigured(
        "No AI provider is configured. " + GeminiProvider.setup_hint()
        + " Alternatively, " + LocalProvider.setup_hint()[0].lower()
        + LocalProvider.setup_hint()[1:]
    )


def status():
    """
    What the UI needs to describe the assistant's state.

    Resolved through resolve() rather than available(), so the panel can
    never say "ready" about a provider that a chat request would reject —
    which is what an explicit MATHNOVA_AI_PROVIDER naming an unconfigured
    backend would otherwise produce.
    """

    try:
        instance = resolve()
    except NotConfigured as error:
        return {
            "enabled": False,
            "provider": None,
            "provider_label": None,
            "model": None,
            "setup_hint": str(error),
        }

    return {
        "enabled": True,
        "provider": instance.name,
        "provider_label": instance.label,
        "model": instance.model,
        "setup_hint": None,
    }


__all__ = [
    "ChatResult",
    "GeminiProvider",
    "LocalProvider",
    "NotConfigured",
    "Provider",
    "ProviderError",
    "REGISTRY",
    "available",
    "configured_name",
    "resolve",
    "status",
]
