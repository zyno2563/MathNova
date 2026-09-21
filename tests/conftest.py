"""
Shared test setup.

backend.config loads the developer's .env at import, so a real
GROQ_API_KEY there would make "auto" route test requests to the live
API — spending the free daily allowance and making results depend on
the network. Tests that want Groq configure it explicitly against a
local stub.
"""

import pytest


@pytest.fixture(autouse=True)
def no_real_groq(monkeypatch):
    for name in ("GROQ_API_KEY", "MATHNOVA_GROQ_BASE_URL",
                 "MATHNOVA_GROQ_MODELS", "MATHNOVA_GROQ_MAX_TOKENS"):
        monkeypatch.delenv(name, raising=False)
