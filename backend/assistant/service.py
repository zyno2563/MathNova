"""
The assistant service: one conversation turn, routed to whichever AI
provider is configured, with the MathNova engines available as tools.
"""

import logging

from backend.assistant import providers
from backend.assistant.tools import TOOLS
from backend.config import settings
from backend.errors import EngineError

logger = logging.getLogger("mathnova.assistant")

SYSTEM_PROMPT = """\
You are the MathNova Mathematics Assistant, helping engineering \
students with engineering mathematics.

MathNova has verified symbolic engines for: Fourier series, calculus, \
linear algebra, ordinary differential equations (complementary \
function, particular integral, complete solution, and first-order \
methods), first-order partial differential equations, numerical \
methods (root finding, differentiation, integration, interpolation, \
linear systems), and Laplace, Fourier and Z-transforms.

You have tools that call those engines directly. Use them whenever a \
concrete result is wanted — do not compute transforms, integrals, \
eigenvalues or ODE solutions yourself. The engines verify their own \
results symbolically, so a tool answer is more trustworthy than your \
recollection. If a tool reports a failure, explain the likely cause \
(usually the input form) and suggest a corrected input.

How to answer:
- Teach, don't just state. Show the method and the key steps.
- Use LaTeX for every mathematical expression: $...$ inline and \
$$...$$ for displayed equations. Never write LaTeX inside code fences.
- Be concise. Prefer short prose and displayed equations over long \
paragraphs.
- When a tool verified a result, say so briefly.
- If a question is outside engineering mathematics, say so and redirect.
"""


def _history(history, message, module_context):
    """Build the provider-neutral conversation."""

    conversation = []

    for entry in (history or [])[-settings.ASSISTANT_HISTORY_LIMIT:]:
        role = entry.get("role")
        content = (entry.get("content") or "").strip()

        if role in ("user", "assistant") and content:
            conversation.append({"role": role, "content": content})

    # Providers expect the exchange to open with a user turn.
    while conversation and conversation[0]["role"] != "user":
        conversation.pop(0)

    text = message

    if module_context:
        text = (
            f"[The student is currently using the {module_context} module.]\n\n"
            f"{message}"
        )

    conversation.append({"role": "user", "content": text})

    return conversation


#: What a visitor is told when the assistant cannot answer. Which
#: provider is configured, which model it runs, and how to set one up
#: are operational details: they identify a vendor and a deployment to
#: anyone who asks the API, so they stay server-side.
UNAVAILABLE_MESSAGE = (
    "The AI assistant is unavailable right now. Every other MathNova "
    "module works without it."
)

BUSY_MESSAGE = (
    "The AI assistant is busy right now. Please wait a moment and try "
    "again."
)

#: Public replacements for provider error messages, which name the
#: vendor, its pricing tier and its models.
#: A daily cap is not "busy": waiting a moment does nothing, and saying
#: so sent people round a retry loop that could never succeed.
DAILY_LIMIT_MESSAGE = (
    "The AI assistant has reached its free usage limit for today. Please "
    "try again later — every other MathNova module works without it."
)

_PUBLIC_MESSAGES = {
    "assistant_unavailable": UNAVAILABLE_MESSAGE,
    "assistant_daily_limit": DAILY_LIMIT_MESSAGE,
    "assistant_rate_limited": BUSY_MESSAGE,
    "assistant_busy": BUSY_MESSAGE,
    "assistant_model_unavailable": UNAVAILABLE_MESSAGE,
    "assistant_error": (
        "The AI assistant could not answer that. Please try again."
    ),
}


def _public_error(error):
    """
    Turn a provider failure into something safe to return.

    The provider's own message is written for whoever runs the server —
    it names the backend, quotes its setup instructions and sometimes
    echoes a request URL — so it is logged rather than sent.
    """

    logger.warning(
        "Assistant unavailable (%s): %s", error.code, error.message
    )

    return EngineError(
        error.status,
        error.code,
        _PUBLIC_MESSAGES.get(error.code, UNAVAILABLE_MESSAGE),
    )


def status():
    """
    Whether the assistant can answer — and nothing about how.

    The full picture (provider, model, setup hint) goes to the log for
    whoever is running the server.
    """

    detail = providers.status()

    if not detail["enabled"]:
        logger.info(
            "Assistant is not configured. %s", detail["setup_hint"] or ""
        )

    return {
        "enabled": detail["enabled"],
        "message": None if detail["enabled"] else UNAVAILABLE_MESSAGE,
    }


#: Failures another provider may not share: limits, overload, a retired
#: or missing model, a backend that is down or unconfigured.
_FALL_THROUGH = {
    "assistant_daily_limit",
    "assistant_rate_limited",
    "assistant_busy",
    "assistant_model_unavailable",
    "assistant_unavailable",
}


def _most_telling(failures):
    """
    Which failure to report when every provider was exhausted.

    "Today's limit is reached" only when that is true of all of them;
    otherwise a shorter wait might work, and saying so is more useful.
    """

    if all(error.code == "assistant_daily_limit" for error in failures):
        return failures[-1]

    for code in ("assistant_rate_limited", "assistant_busy"):
        for error in failures:
            if error.code == code:
                return error

    return failures[-1]


def chat(message, history=None, module_context=None):
    """Run one assistant turn and return the reply plus any tools used."""

    try:
        candidates = providers.chain()
    except providers.ProviderError as error:
        raise _public_error(error)

    conversation = _history(history, message, module_context)

    result = None
    failures = []

    for provider in candidates:
        try:
            result = provider.chat(
                system=SYSTEM_PROMPT,
                messages=conversation,
                tools=TOOLS,
                max_tool_turns=settings.ASSISTANT_MAX_TOOL_TURNS,
                max_output_tokens=settings.ASSISTANT_MAX_TOKENS,
            )
            break
        except providers.ProviderError as error:
            failures.append(error)

            if error.code not in _FALL_THROUGH:
                # Not a capacity problem: another provider would not help.
                raise _public_error(error)

            logger.warning(
                "Provider %s could not answer (%s); trying the next one",
                provider.name, error.code,
            )
        except Exception:  # noqa: BLE001 - last line of defence
            logger.exception("Assistant turn failed")
            raise EngineError(
                502,
                "assistant_error",
                _PUBLIC_MESSAGES["assistant_error"],
            )

    if result is None:
        raise _public_error(_most_telling(failures))

    payload = result.as_dict()

    # The reply carries which MathNova engines ran, which is worth
    # showing. Which model produced the prose around them is not, and
    # would name the vendor on every single answer.
    payload.pop("provider", None)
    payload.pop("model", None)

    if not payload["reply"]:
        payload["reply"] = (
            "I used up my tool steps on that one before reaching an "
            "answer. Try narrowing the question, or work it through in "
            "the matching MathNova module directly."
            if payload["truncated"] else
            "I wasn't able to produce an answer for that. Try rephrasing, "
            "or use the matching MathNova module directly."
        )

    return payload
