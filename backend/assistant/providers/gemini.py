"""
Google Gemini provider — the default cloud backend.

Uses the Gemini API free tier: an API key from Google AI Studio with no
billing account attached. Automatic function calling is switched off so
the loop stays here, which keeps tool accounting and the turn ceiling
identical across providers.
"""

import logging
import os
import re

from backend.config import settings
from backend.assistant.providers.base import (
    ChatResult,
    NotConfigured,
    Provider,
    ProviderError,
    run_tool,
)

logger = logging.getLogger("mathnova.assistant.gemini")

# Free-tier default. Any model the key can reach works; override with
# MATHNOVA_AI_MODEL.
#
# Google retires older models for *new* API keys while still listing them
# in models.list(), so a model being listed does not mean it can be
# called. Keep this on a current flash model; the 404 path below prints
# Google's own replacement suggestion when this one ages out.
DEFAULT_MODEL = "gemini-3.6-flash"


def _api_message(text):
    """Pull the human-readable 'message' out of a Google API error blob."""

    match = re.search(r"'message':\s*'([^']+)'", text) or re.search(
        r'"message":\s*"([^"]+)"', text
    )

    return match.group(1).strip() if match else ""


def _api_key():
    # GOOGLE_API_KEY is what the SDK itself reads; accept both so an
    # existing Google setup works untouched.
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(name, "").strip()

        if value:
            return value

    return ""


class GeminiProvider(Provider):
    name = "gemini"
    label = "Google Gemini (free tier)"

    def __init__(self, model=None, base_url=None):
        self._model = (
            model
            or os.getenv("MATHNOVA_AI_MODEL", "").strip()
            or DEFAULT_MODEL
        )
        self._base_url = base_url or os.getenv(
            "MATHNOVA_GEMINI_BASE_URL", ""
        ).strip()
        self._client = None

    # ---------------------------------------------------------

    @classmethod
    def is_configured(cls):
        if not _api_key():
            return False

        try:
            import google.genai  # noqa: F401
        except ImportError:
            return False

        return True

    @classmethod
    def setup_hint(cls):
        return (
            "Create a free API key at https://aistudio.google.com/apikey "
            "and set GEMINI_API_KEY in the server environment. No billing "
            "account is required."
        )

    @property
    def model(self):
        return self._model

    # ---------------------------------------------------------

    def _get_client(self):
        if self._client is not None:
            return self._client

        key = _api_key()

        if not key:
            raise NotConfigured(
                "The AI assistant is not configured. " + self.setup_hint()
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise NotConfigured(
                "The google-genai package is not installed. "
                "Run: pip install google-genai"
            )

        # Always set a timeout: without one a stalled connection holds
        # the worker for as long as the peer keeps the socket open.
        # HttpOptions takes milliseconds.
        options = types.HttpOptions(
            timeout=int(settings.ASSISTANT_TIMEOUT * 1000)
        )

        if self._base_url:
            options.base_url = self._base_url

        self._client = genai.Client(api_key=key, http_options=options)

        return self._client

    def _declarations(self, tools):
        from google.genai import types

        return [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters_json_schema=tool.parameters,
                )
                for tool in tools
            ])
        ]

    def _history(self, messages):
        from google.genai import types

        contents = []

        for entry in messages:
            role = entry.get("role")
            text = (entry.get("content") or "").strip()

            if not text or role not in ("user", "assistant"):
                continue

            contents.append(types.Content(
                # Gemini names the assistant turn "model".
                role="model" if role == "assistant" else "user",
                parts=[types.Part.from_text(text=text)],
            ))

        return contents

    # ---------------------------------------------------------

    def chat(self, system, messages, tools, max_tool_turns=8,
             max_output_tokens=None):
        from google.genai import types

        client = self._get_client()
        tools_by_name = {tool.name: tool for tool in tools}

        contents = self._history(messages)

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=self._declarations(tools),
            # Drive the loop here so tool use is observable and bounded.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            max_output_tokens=max_output_tokens,
        )

        tools_used = []
        reply_parts = []
        truncated = False

        for turn in range(max_tool_turns):
            try:
                response = client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            except Exception as error:  # noqa: BLE001
                raise self._translate(error)

            candidate = (response.candidates or [None])[0]

            if candidate is None or candidate.content is None:
                break

            parts = candidate.content.parts or []
            calls = [part.function_call for part in parts if part.function_call]

            for part in parts:
                if part.text:
                    reply_parts.append(part.text)

            if not calls:
                break

            # Echo the model turn back, then answer every call it made.
            contents.append(candidate.content)

            responses = []

            for call in calls:
                tools_used.append(call.name)
                output = run_tool(tools_by_name, call.name, dict(call.args or {}))
                responses.append(types.Part.from_function_response(
                    name=call.name,
                    response={"result": output},
                ))

            contents.append(types.Content(role="user", parts=responses))

            if turn == max_tool_turns - 1:
                truncated = True

        return ChatResult(
            reply="\n".join(part.strip() for part in reply_parts if part).strip(),
            tools_used=tools_used,
            model=self._model,
            provider=self.name,
            truncated=truncated,
        )

    # ---------------------------------------------------------

    def _translate(self, error):
        """Map SDK/API failures onto messages worth showing a student."""

        text = str(error)
        lowered = text.lower()

        if "api key" in lowered or "unauthenticated" in lowered or "401" in text:
            return NotConfigured(
                "The configured Gemini API key was rejected. " + self.setup_hint()
            )

        if "429" in text or "resource_exhausted" in lowered or "quota" in lowered:
            # The free tier's binding limit is per *day* (20 requests per
            # model), and "wait a moment" is wrong advice for that one.
            # Google names the quota that tripped, e.g.
            # GenerateRequestsPerDayPerProjectPerModel-FreeTier.
            if "perday" in lowered or "per day" in lowered:
                return ProviderError(
                    "The Gemini free tier daily limit was reached. It resets "
                    "at midnight Pacific time.",
                    status=429,
                    code="assistant_daily_limit",
                )

            return ProviderError(
                "The Gemini free tier rate limit was reached. Wait a moment "
                "and try again.",
                status=429,
                code="assistant_rate_limited",
            )

        if "503" in text or "unavailable" in lowered or "overloaded" in lowered:
            # Free-tier capacity, not a fault in the request. Seen in
            # normal use, so it gets its own retryable message rather
            # than the generic one.
            return ProviderError(
                "The AI model is busy right now. This is temporary — "
                "please send your question again in a moment.",
                status=503,
                code="assistant_busy",
            )

        if "404" in text or "not found" in lowered:
            # Google's own message names the replacement model when one
            # has been retired, so pass it through rather than replacing
            # it with a generic line that hides the fix.
            return ProviderError(
                f"The model '{self._model}' could not be used. "
                + _api_message(text)
                + " Set MATHNOVA_AI_MODEL to a model your key can use.",
                status=502,
                code="assistant_model_unavailable",
            )

        logger.exception("Gemini request failed")

        return ProviderError(
            "The AI provider returned an error. Please try again.",
            status=502,
            code="assistant_error",
        )
