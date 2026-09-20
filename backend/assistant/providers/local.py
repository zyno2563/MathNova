"""
Local-model provider — an offline fallback.

Talks to an Ollama-compatible server (default http://localhost:11434)
over its native /api/chat endpoint, which supports tool calling. Uses
only the standard library, so enabling it costs no dependency and no
API key.

Start one with:

    ollama serve
    ollama pull llama3.1        # any tool-calling model
"""

import json
import logging
import os
import urllib.error
import urllib.request

from backend.config import settings
from backend.assistant.providers.base import (
    ChatResult,
    NotConfigured,
    Provider,
    ProviderError,
    run_tool,
)

logger = logging.getLogger("mathnova.assistant.local")

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"


class LocalProvider(Provider):
    name = "local"
    label = "Local model (Ollama)"

    def __init__(self, base_url=None, model=None, timeout=None):
        self._base_url = (
            base_url
            or os.getenv("MATHNOVA_LOCAL_AI_URL", "").strip()
            or DEFAULT_URL
        ).rstrip("/")
        self._model = (
            model
            or os.getenv("MATHNOVA_LOCAL_AI_MODEL", "").strip()
            or DEFAULT_MODEL
        )
        # Bounded for the same reason as the cloud provider: a local
        # model that wedges must not hold the request open forever.
        self._timeout = timeout or settings.ASSISTANT_TIMEOUT

    # ---------------------------------------------------------

    @classmethod
    def is_configured(cls):
        """
        Only claim availability if a server actually answers.

        A local model is opt-in: probing keeps `auto` selection from
        picking a backend that is not running.
        """

        if os.getenv("MATHNOVA_LOCAL_AI_ENABLED", "").strip().lower() not in (
            "1", "true", "yes", "on"
        ):
            return False

        return cls(timeout=2)._reachable()

    @classmethod
    def setup_hint(cls):
        return (
            "Run a local Ollama server (`ollama serve`, then "
            "`ollama pull llama3.1`) and set MATHNOVA_LOCAL_AI_ENABLED=1."
        )

    @property
    def model(self):
        return self._model

    # ---------------------------------------------------------

    def _reachable(self):
        try:
            with urllib.request.urlopen(
                f"{self._base_url}/api/tags", timeout=self._timeout
            ) as response:
                return response.status == 200
        except Exception:  # noqa: BLE001 - absence is the normal case
            return False

    def _post(self, path, payload):
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")[:200]

            if error.code == 404:
                raise ProviderError(
                    f"The local model '{self._model}' is not installed. "
                    f"Run: ollama pull {self._model}",
                    status=502,
                    code="assistant_model_unavailable",
                )

            raise ProviderError(
                f"The local model server returned {error.code}: {body}",
                status=502,
                code="assistant_error",
            )
        except urllib.error.URLError as error:
            raise NotConfigured(
                f"No local model server at {self._base_url} ({error.reason}). "
                + self.setup_hint()
            )

    def _declarations(self, tools):
        return [
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

    # ---------------------------------------------------------

    def chat(self, system, messages, tools, max_tool_turns=8,
             max_output_tokens=None):
        tools_by_name = {tool.name: tool for tool in tools}

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
            payload = self._post("/api/chat", {
                "model": self._model,
                "messages": history,
                "tools": self._declarations(tools),
                "stream": False,
                "options": ({"num_predict": max_output_tokens}
                            if max_output_tokens else {}),
            })

            message = payload.get("message") or {}
            calls = message.get("tool_calls") or []

            if message.get("content"):
                reply = message["content"]

            if not calls:
                break

            history.append(message)

            for call in calls:
                function = call.get("function") or {}
                name = function.get("name", "")
                arguments = function.get("arguments") or {}

                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except ValueError:
                        arguments = {}

                tools_used.append(name)

                history.append({
                    "role": "tool",
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
