"""
Shared input limits for the API surface.

Two jobs:

* Reusable field constraints, so every numeric input is finite and
  bounded and every collection has a ceiling. Left unbounded, a float
  field accepts `Infinity` and `NaN` — JSON's parser produces them and
  Pydantic passes them straight through — and the engines then return a
  confident-looking answer built from a non-number.

* A cap on the request body itself, applied before the body is read, so
  an oversized payload is refused rather than buffered.

The numbers here are deliberately generous for engineering mathematics
and deliberately far below what would threaten the server.
"""

from pydantic import Field
from starlette.responses import JSONResponse

from backend.config import settings

#: Largest magnitude accepted for any numeric input. Engineering inputs
#: live far below this; beyond it, floating-point steps lose meaning.
MAGNITUDE = 1e9

#: Data-series ceiling. Interpolation is O(n^2) symbolically, so the
#: point count is what actually has to be bounded.
MAX_POINTS = 200

#: Prior turns the assistant will accept in one request.
MAX_HISTORY_TURNS = 20


def number(description=None, default=..., **constraints):
    """
    A finite, bounded numeric field.

    `allow_inf_nan=False` is the part that matters: a bounded field
    already rejects NaN (every comparison against it is false), but an
    optional one with no bounds does not, and Infinity survives both.
    """

    constraints.setdefault("ge", -MAGNITUDE)
    constraints.setdefault("le", MAGNITUDE)

    return Field(
        default,
        description=description,
        allow_inf_nan=False,
        **constraints
    )


class BodySizeLimitMiddleware:
    """
    Refuse oversized request bodies before reading them.

    Pure ASGI rather than BaseHTTPMiddleware so the check happens at the
    protocol level: a declared Content-Length is rejected outright, and
    a chunked body is measured as it streams and cut off once it passes
    the limit, instead of being buffered first.
    """

    def __init__(self, app, max_bytes=None):
        self.app = app
        self.max_bytes = max_bytes or settings.MAX_REQUEST_BYTES

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or ())
        declared = headers.get(b"content-length")

        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(scope, send)
                    return
            except ValueError:
                pass

        received = 0

        async def measured_receive():
            nonlocal received

            message = await receive()

            if message["type"] == "http.request":
                received += len(message.get("body", b""))

                if received > self.max_bytes:
                    # Stop the stream; the endpoint sees a truncated body
                    # and fails validation rather than consuming the rest.
                    raise _BodyTooLarge()

            return message

        try:
            await self.app(scope, measured_receive, send)
        except _BodyTooLarge:
            await self._reject(scope, send)

    async def _reject(self, scope, send):
        response = JSONResponse(
            status_code=413,
            content={
                "ok": False,
                "error": {
                    "code": "request_too_large",
                    "message": (
                        f"The request body is larger than the "
                        f"{self.max_bytes // 1024} KB limit."
                    )
                }
            }
        )

        await response(scope, lambda: None, send)


class _BodyTooLarge(Exception):
    """Internal signal from the receive wrapper."""
