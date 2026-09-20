"""
Uniform error contract for the MathNova API.

Every failure reaches the client as:

    {"ok": false, "error": {"code": ..., "message": ...}}

`solve()` wraps a call into a core engine. The engines raise plain
Python exceptions (mostly ValueError) for bad mathematical input, so
those are translated into 4xx responses carrying the engine's own
message, which is already written for a student to read.
"""

import logging
import os
import re

import sympy as sp
from fastapi import HTTPException

from backend.compute import (
    ComputationTimeout,
    ComputationTooLarge,
    ResultNotTransferable,
    run_guarded,
)

logger = logging.getLogger("mathnova")


#: Environment variables whose values must never reach a client.
_SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")

#: A source file quoted with its directory, e.g. /srv/app/lib/parser.py.
#: The filename is useful in a message; where it lives on disk is not.
_SOURCE_FILE = re.compile(r"(?:/[\w.@+-]+)+/([\w.-]+\.(?:py|pyc|so))")

#: A directory path rooted somewhere only the server knows about. Anchored
#: to real filesystem roots rather than to "starts with a slash", so URLs
#: — which appear legitimately in setup hints — are left intact.
_SERVER_PATH = re.compile(
    r"(?<![\w/])"
    r"(?:/(?:Users|home|root|var|tmp|opt|srv|app|private|usr|etc|mnt)"
    r"(?:/[\w.@+-]+)+/?"
    r"|[A-Za-z]:\\(?:[\w.@+ -]+\\?)+)"
)

MAX_MESSAGE_CHARS = 400


def _secrets():
    """Current secret values, read fresh so tests and reloads see them."""

    found = []

    for name, value in os.environ.items():
        if not value or len(value) < 8:
            continue

        if any(hint in name.upper() for hint in _SECRET_HINTS):
            found.append(value)

    return found


def sanitize(message):
    """
    Make an error message safe to return to a client.

    Engine and provider messages are written for a student and are
    normally fine, but they are not authored with a client in mind: a
    provider can echo a request URL carrying an API key, and a library
    can quote the file it failed in. Neither belongs in a response.
    """

    text = str(message)

    for secret in _secrets():
        text = text.replace(secret, "[redacted]")

    # Keep the filename, drop the directory it lives in.
    text = _SOURCE_FILE.sub(r"\1", text)
    text = _SERVER_PATH.sub("[path]", text)

    if len(text) > MAX_MESSAGE_CHARS:
        text = text[:MAX_MESSAGE_CHARS].rstrip() + "…"

    return text


def _direct(function, *args, **kwargs):
    """Run in the current process, without isolation."""

    return function(*args, **kwargs)


class EngineError(HTTPException):
    """An engine rejected the request or could not produce a result."""

    def __init__(self, status_code, code, message):
        message = sanitize(message)
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message


class InvalidInput(EngineError):
    def __init__(self, message):
        super().__init__(400, "invalid_input", message)


class Unsolvable(EngineError):
    def __init__(self, message):
        super().__init__(422, "unsolvable", message)


class TooExpensive(EngineError):
    """The calculation was abandoned before it could finish."""

    def __init__(self, message):
        super().__init__(503, "computation_too_expensive", message)


# Exceptions that mean "the request was mathematically invalid",
# not "the server is broken".
_INPUT_ERRORS = (
    ValueError,
    TypeError,
    SyntaxError,
    ZeroDivisionError,
    ArithmeticError,
    IndexError,
    KeyError,
    AttributeError,
    sp.SympifyError,
)


def solve(operation, function, *args, isolated=True, **kwargs):
    """
    Call a core engine function and translate failures.

    `operation` is a short human-readable label used in the error
    message so the client knows which step failed.

    `isolated=False` runs the call in-process. It is for the rare step
    that returns a live Python object — a lambdified callable cannot be
    sent back from a child process. Use it only for cheap steps, and
    keep the expensive symbolic work under the guard.
    """

    runner = run_guarded if isolated else _direct

    try:
        # Engines run in a disposable child process under a deadline and
        # a memory cap, so no single input can hang or exhaust the
        # worker handling the request. See backend/compute.py.
        return runner(function, *args, **kwargs)

    except EngineError:
        raise

    except ComputationTimeout as error:
        logger.warning("%s exceeded the %ss deadline", operation, error)
        raise TooExpensive(
            f"{operation}: this took too long and was stopped. Try a "
            f"simpler expression."
        )

    except ResultNotTransferable as error:
        # Never a client's fault: the endpoint asked the guard to return
        # something that cannot leave a child process.
        logger.error(
            "%s returned a %s, which cannot cross a process boundary; "
            "this call needs solve(..., isolated=False)", operation, error
        )
        raise EngineError(
            500, "internal_error", f"{operation}: unexpected server error"
        )

    except ComputationTooLarge:
        logger.warning("%s exhausted its memory allowance", operation)
        raise TooExpensive(
            f"{operation}: this needed too much memory and was stopped. "
            f"Try a simpler expression."
        )

    except NotImplementedError as error:
        raise Unsolvable(
            f"{operation}: this case is not supported yet"
            + (f" ({error})" if str(error) else "")
        )

    except RecursionError:
        raise Unsolvable(
            f"{operation}: the expression was too deeply nested to evaluate"
        )

    except _INPUT_ERRORS as error:
        message = str(error).strip() or error.__class__.__name__
        raise InvalidInput(f"{operation}: {message}")

    except Exception as error:  # noqa: BLE001 - last line of defence
        logger.exception("Unhandled engine failure during %s", operation)
        raise EngineError(
            500,
            "internal_error",
            f"{operation}: unexpected server error ({error.__class__.__name__})"
        )
