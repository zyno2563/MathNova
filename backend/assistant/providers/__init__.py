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
from backend.assistant.providers.groq import GroqProvider
from backend.assistant.providers.local import LocalProvider

REGISTRY = {
    GroqProvider.name: GroqProvider,
    GeminiProvider.name: GeminiProvider,
    LocalProvider.name: LocalProvider,
}

#: Tried in order when MATHNOVA_AI_PROVIDER is "auto". Groq's free tier
#: is far larger than Gemini's, so it leads; Gemini picks up when Groq's
#: allowance for the day is spent.
PREFERENCE = (GroqProvider, GeminiProvider, LocalProvider)


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
        "No AI provider is configured. " + GroqProvider.setup_hint()
        + " Or: " + GeminiProvider.setup_hint()
    )


def chain():
    """
    Providers to try for one request, in order.

    With "auto", every configured provider — so when one reaches its free
    limit the request falls through to the next. An explicit choice is
    honoured alone, never silently widened.
    """

    if configured_name() != "auto":
        return [resolve()]

    ready = [cls() for cls in PREFERENCE if cls.is_configured()]

    if not ready:
        resolve()  # raises the explanatory NotConfigured

    return ready


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
    "GroqProvider",
    "LocalProvider",
    "NotConfigured",
    "Provider",
    "ProviderError",
    "REGISTRY",
    "available",
    "chain",
    "configured_name",
    "resolve",
    "status",
]
