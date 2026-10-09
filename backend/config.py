"""Environment-driven settings for the MathNova backend."""

import os

try:
    from dotenv import load_dotenv

    # Real environment variables always win over the file.
    load_dotenv(override=False)
except ImportError:  # python-dotenv is optional at runtime
    pass


def _flag(name, default="0"):
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Runtime configuration, read once at import."""

    APP_NAME = "MathNova"
    APP_VERSION = "1.0.0"

    # Assistant. Which backend answers is decided by the provider
    # registry (backend/assistant/providers), so no vendor is named here.
    AI_PROVIDER = os.getenv("MATHNOVA_AI_PROVIDER", "auto").strip().lower()
    # Ceiling on a single reply: high enough not to truncate a worked
    # solution mid-derivation, low enough to stay inside HTTP timeouts.
    ASSISTANT_MAX_TOKENS = int(
        os.getenv("MATHNOVA_ASSISTANT_MAX_TOKENS", "16000")
    )
    # Bound the agentic loop so a pathological conversation cannot
    # spin against a provider's rate limit.
    ASSISTANT_MAX_TOOL_TURNS = int(
        os.getenv("MATHNOVA_ASSISTANT_MAX_TOOL_TURNS", "8")
    )
    ASSISTANT_HISTORY_LIMIT = int(
        os.getenv("MATHNOVA_ASSISTANT_HISTORY_LIMIT", "20")
    )

    # Bounded execution for the symbolic engines. The deadline is a
    # safety net against pathological input, not a latency target: a
    # legitimate hard integral can legitimately take several seconds.
    COMPUTE_TIMEOUT = float(os.getenv("MATHNOVA_COMPUTE_TIMEOUT", "30"))
    COMPUTE_MEMORY_MB = int(os.getenv("MATHNOVA_COMPUTE_MEMORY_MB", "1024"))

    ADMISSION_ENABLED = _flag("MATHNOVA_ADMISSION_ENABLED", "1")
    MAX_ACTIVE_REQUESTS = max(1, int(os.getenv("MATHNOVA_MAX_ACTIVE_REQUESTS", "1")))
    MAX_QUEUED_REQUESTS = max(0, int(os.getenv("MATHNOVA_MAX_QUEUED_REQUESTS", "2")))
    QUEUE_WAIT_SECONDS = float(os.getenv("MATHNOVA_QUEUE_WAIT_SECONDS", "5"))
    REQUEST_TIMEOUT = float(os.getenv("MATHNOVA_REQUEST_TIMEOUT", "90"))
    REQUESTS_PER_MINUTE = max(1, int(os.getenv("MATHNOVA_REQUESTS_PER_MINUTE", "30")))
    AI_REQUESTS_PER_MINUTE = max(1, int(os.getenv("MATHNOVA_AI_REQUESTS_PER_MINUTE", "5")))
    AI_GLOBAL_REQUESTS_PER_MINUTE = max(1, int(os.getenv("MATHNOVA_AI_GLOBAL_REQUESTS_PER_MINUTE", "10")))

    # How long the assistant may wait on its provider. Kept well under a
    # typical proxy's 60s so the client sees our error, not a gateway's.
    ASSISTANT_TIMEOUT = float(os.getenv("MATHNOVA_ASSISTANT_TIMEOUT", "45"))

    # Largest request body accepted. Every legitimate MathNova request
    # is a few hundred bytes; this only has to stop a flood.
    MAX_REQUEST_BYTES = int(os.getenv("MATHNOVA_MAX_REQUEST_BYTES", str(128 * 1024)))

    # CORS: comma-separated origins. Default is same-origin only,
    # which is what the bundled frontend needs — it is served by this
    # same app, so no cross-origin request is involved at all.
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("MATHNOVA_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]

    DEBUG = _flag("MATHNOVA_DEBUG")

    #: Origins a developer's own tooling runs on. Added only in DEBUG,
    #: so a production deploy never trusts localhost.
    DEV_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    @property
    def cors_origins(self):
        """
        The origins actually allowed, and whether any are.

        A wildcard is honoured only in DEBUG. In production it would let
        any site on the internet drive this API from a visitor's
        browser, and it is almost always a copied-in default rather than
        a decision, so it is dropped with a warning instead.
        """

        import logging

        origins = list(self.CORS_ORIGINS)

        if "*" in origins:
            origins = [origin for origin in origins if origin != "*"]

            if self.DEBUG:
                return ["*"]

            logging.getLogger("mathnova").warning(
                "MATHNOVA_CORS_ORIGINS contains '*', which is refused "
                "outside debug mode. List the exact origins instead."
            )

        if self.DEBUG:
            origins.extend(
                origin for origin in self.DEV_ORIGINS if origin not in origins
            )

        return origins

    @property
    def assistant_enabled(self):
        # Delegated so adding a provider needs no change here. Imported
        # lazily: config must stay importable without the AI extras.
        from backend.assistant import providers

        return bool(providers.available())


settings = Settings()
