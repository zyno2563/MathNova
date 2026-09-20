"""
The contract every AI provider implements.

A provider receives a system prompt, a conversation, and the MathNova
tool list, and returns a finished reply. Running the tool loop is the
provider's job because each API expresses function calling differently;
everything above this layer stays provider-neutral.
"""

from typing import Dict, List, Optional


class ProviderError(Exception):
    """A provider failed in a way worth reporting to the user."""

    def __init__(self, message, status=502, code="assistant_error"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class NotConfigured(ProviderError):
    """The provider has no credentials or no reachable endpoint."""

    def __init__(self, message):
        super().__init__(message, status=503, code="assistant_unavailable")


class ChatResult:
    """What every provider returns, regardless of vendor."""

    def __init__(self, reply, tools_used=None, model=None,
                 provider=None, truncated=False):
        self.reply = reply
        self.tools_used = sorted(set(tools_used or []))
        self.model = model
        self.provider = provider
        self.truncated = truncated

    def as_dict(self):
        return {
            "reply": self.reply,
            "tools_used": self.tools_used,
            "model": self.model,
            "provider": self.provider,
            "truncated": self.truncated,
        }


class Provider:
    """Base class for AI providers."""

    #: short identifier used in configuration, e.g. "gemini"
    name = "provider"

    #: human-readable label for the UI
    label = "AI provider"

    @classmethod
    def is_configured(cls) -> bool:
        """True when this provider could serve a request right now."""

        raise NotImplementedError

    @classmethod
    def setup_hint(cls) -> str:
        """One line telling the operator how to enable this provider."""

        raise NotImplementedError

    @property
    def model(self) -> str:
        raise NotImplementedError

    def chat(
        self,
        system: str,
        messages: List[Dict[str, str]],
        tools: List,
        max_tool_turns: int = 8,
        max_output_tokens: Optional[int] = None,
    ) -> ChatResult:
        """
        Run one assistant turn.

        `messages` is a list of {"role": "user"|"assistant", "content": str},
        oldest first, ending with the current user message.
        """

        raise NotImplementedError


def run_tool(tools_by_name, name, arguments):
    """
    Execute a tool by name, returning text for the model.

    Never raises: an unknown tool or a failing engine comes back as a
    message the model can read and recover from.
    """

    tool = tools_by_name.get(name)

    if tool is None:
        return f"No such tool: {name}"

    return tool.run(arguments)
