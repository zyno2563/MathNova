"""
Groq provider — the primary free cloud backend.

Groq's free tier needs no card and allows far more than Gemini's free
tier (whose limit is 20 requests per model per day). It speaks the
OpenAI-compatible chat-completions API, which is also what OpenRouter
and several other hosts expose, so pointing MATHNOVA_GROQ_BASE_URL
elsewhere is all it takes to use one of them instead.

Free-tier limits are set per model, so a list of models is tried in
order: when one reaches its limit the same request moves to the next.

Standard library only, like the local provider: no SDK, no dependency.
"""

import json
import logging
import os
import urllib.error
import urllib.request

from backend.assistant.providers.base import (
    ChatResult,
    NotConfigured,
    Provider,
    ProviderError,
    run_tool,
)
from backend.config import settings

logger = logging.getLogger("mathnova.assistant.groq")

DEFAULT_URL = "https://api.groq.com/openai/v1"

#: Tried in order. All three support tool calling on Groq's free tier,
#: and each has its own daily allowance.
DEFAULT_MODELS = (
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
)

#: Groq checks a request's prompt *plus* its max output against the
#: per-minute token limit (a few thousand on the free tier), so asking
#: for the app-wide 16,000 would refuse every request outright. This is
#: still ample for a worked explanation.
DEFAULT_MAX_TOKENS = 2048


class _ModelExhausted(Exception):
    """This model cannot take the request now; the next one might."""

    def __init__(self, error):
        super().__init__(error.message)
        self.error = error


def _api_key():
    return os.getenv("GROQ_API_KEY", "").strip()


class GroqProvider(Provider):
    name = "groq"
    label = "Groq (free tier)"

    def __init__(self, models=None, base_url=None, timeout=None,
                 max_tokens=None):
        configured = os.getenv("MATHNOVA_GROQ_MODELS", "").strip()

        self._models = list(
            models
            or [m.strip() for m in configured.split(",") if m.strip()]
            or DEFAULT_MODELS
        )
        self._base_url = (
            base_url
            or os.getenv("MATHNOVA_GROQ_BASE_URL", "").strip()
            or DEFAULT_URL
        ).rstrip("/")
        self._timeout = timeout or settings.ASSISTANT_TIMEOUT
        self._max_tokens = max_tokens or int(
            os.getenv("MATHNOVA_GROQ_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        )
        self._model = self._models[0]

    # ---------------------------------------------------------

    @classmethod
    def is_configured(cls):
        return bool(_api_key())

    @classmethod
    def setup_hint(cls):
        return (
            "Create a free API key at https://console.groq.com/keys (no "
            "card needed) and set GROQ_API_KEY in the server environment."
        )

    @property
    def model(self):
        return self._model

    # ---------------------------------------------------------

    def _post(self, payload):
        key = _api_key()

        if not key:
            raise NotConfigured(
                "The AI assistant is not configured. " + self.setup_hint()
            )

        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                # Groq's edge rejects urllib's default agent string.
                "User-Agent": "MathNova/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise self._translate(error.code, error.read().decode(errors="replace"))
        except urllib.error.URLError as error:
            raise ProviderError(
                f"The AI provider could not be reached ({error.reason}).",
                status=503,
                code="assistant_busy",
            )
        except (TimeoutError, OSError) as error:
            raise ProviderError(
                f"The AI provider did not answer in time ({error}).",
                status=503,
                code="assistant_busy",
            )

    def _translate(self, status, body):
        """
        Classify an HTTP failure.

        Limits and a missing or retired model are raised as
        _ModelExhausted, so the caller can move to the next model.
        """

        try:
            message = json.loads(body)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = body[:300]

        lowered = message.lower()

        if status in (401, 403):
            return NotConfigured(
                "The configured Groq API key was rejected. " + self.setup_hint()
            )

        if status in (413, 429):
            daily = (
                "per day" in lowered
                or "(rpd)" in lowered
                or "(tpd)" in lowered
            )

            return _ModelExhausted(ProviderError(
                f"{self._model}: {message}",
                status=429,
                code="assistant_daily_limit" if daily else "assistant_rate_limited",
            ))

        if status == 404 or "decommissioned" in lowered or "model_not_found" in lowered:
            return _ModelExhausted(ProviderError(
                f"{self._model}: {message}",
                status=502,
                code="assistant_model_unavailable",
            ))

        if status >= 500:
            return ProviderError(
                f"The AI provider is having trouble ({status}): {message}",
                status=503,
                code="assistant_busy",
            )

        logger.error("Groq request failed (%s): %s", status, message)

        return ProviderError(
            f"The AI provider rejected the request ({status}): {message}",
            status=502,
            code="assistant_error",
        )

    def _complete(self, messages, tools):
        """One chat-completions call, moving down the model list on limits."""

        last = None

        while True:
            payload = {
                "model": self._model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": self._max_tokens,
            }

            try:
                return self._post(payload)
            except _ModelExhausted as exhausted:
                last = exhausted.error
                logger.warning("Groq model unavailable: %s", last.message)

                position = self._models.index(self._model)

                if position + 1 >= len(self._models):
                    # Every model is spent; report the last reason.
                    raise last

                self._model = self._models[position + 1]

    # ---------------------------------------------------------

    def chat(self, system, messages, tools, max_tool_turns=8,
             max_output_tokens=None):
        tools_by_name = {tool.name: tool for tool in tools}

        declarations = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

        history = [{"role": "system", "content": system}]

        for entry in messages:
            role = entry.get("role")
            text = (entry.get("content") or "").strip()

            if text and role in ("user", "assistant"):
                history.append({"role": role, "content": text})

        tools_used = []
        reply = ""
        truncated = False

        for turn in range(max_tool_turns):
            response = self._complete(history, declarations)

            choice = (response.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            calls = message.get("tool_calls") or []

            if message.get("content"):
                reply = message["content"]

            if not calls:
                break

            # Echo only the fields the API accepts back: reasoning models
            # add extra ones that a follow-up request would reject.
            history.append({
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": calls,
            })

            for call in calls:
                function = call.get("function") or {}
                name = function.get("name", "")
                arguments = function.get("arguments") or "{}"

                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except ValueError:
                        arguments = {}

                tools_used.append(name)

                history.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": run_tool(tools_by_name, name, arguments),
                })

            if turn == max_tool_turns - 1:
                truncated = True

        return ChatResult(
            reply=reply.strip(),
            tools_used=tools_used,
            model=self._model,
            provider=self.name,
            truncated=truncated,
        )
