"""Bound public API traffic before allocating calculation processes.

Limits are per application process. Production uses one Uvicorn worker;
multiple workers/replicas need a shared limiter instead. Client identity
comes from ASGI's trusted peer, never from arbitrary forwarded headers.
"""

import asyncio
import math
import time
from collections import OrderedDict, deque
from contextlib import suppress
from threading import Lock

from starlette.responses import JSONResponse

from backend.config import settings
from backend.request_budget import Budget, RequestStopped, current_budget


class AdmissionMiddleware:
    def __init__(self, app):
        self.app = app
        self.lock = Lock()
        self.active = 0
        self.queue = deque()
        self.visitors = OrderedDict()
        self.ai_times = deque()

    def rate_limit(self, peer, assistant):
        now = time.monotonic()
        window = 60
        limit = settings.AI_REQUESTS_PER_MINUTE if assistant else settings.REQUESTS_PER_MINUTE
        key = (peer, assistant)
        with self.lock:
            # Bound memory even when presented with many different peers.
            for stale in list(self.visitors):
                if not self.visitors[stale] or self.visitors[stale][-1] <= now - window:
                    del self.visitors[stale]
            times = self.visitors.get(key, deque())
            while times and times[0] <= now - window:
                times.popleft()
            while self.ai_times and self.ai_times[0] <= now - window:
                self.ai_times.popleft()
            if len(times) >= limit:
                return max(1, math.ceil(window - (now - times[0])))
            if assistant and len(self.ai_times) >= settings.AI_GLOBAL_REQUESTS_PER_MINUTE:
                return max(1, math.ceil(window - (now - self.ai_times[0])))
            if key not in self.visitors and len(self.visitors) >= 4096:
                return 60
            times.append(now)
            self.visitors[key] = times
            if assistant:
                self.ai_times.append(now)
        return 0

    async def reject(self, scope, receive, send, code, message, status=503, retry=2):
        response = JSONResponse(
            {"ok": False, "error": {"code": code, "message": message}},
            status_code=status, headers={"Retry-After": str(retry)}
        )
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)

        if not settings.ADMISSION_ENABLED:
            return await self.app(scope, receive, send)

        assistant = scope["path"] == "/api/assistant/chat"
        peer = (scope.get("client") or ("unknown",))[0]
        retry = self.rate_limit(peer, assistant)
        if retry:
            return await self.reject(scope, receive, send, "rate_limited",
                f"Too many requests. Please wait {retry} seconds before trying again.", 429, retry)

        budget = Budget(settings.REQUEST_TIMEOUT)
        # BodySizeLimitMiddleware is outside this middleware. Buffer only its
        # bounded body, then give the endpoint its own replay receiver while
        # independently watching for a client disconnect.
        body = []
        try:
            while True:
                message = await asyncio.wait_for(receive(), budget.remaining())
                if message["type"] == "http.disconnect":
                    return
                body.append(message)
                if not message.get("more_body", False):
                    break
        except (asyncio.TimeoutError, RequestStopped):
            return await self.reject(scope, receive, send, "request_timeout", "The request took too long. Please try again.")

        disconnected = asyncio.Event()

        async def watch_disconnect():
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    budget.cancelled.set()
                    disconnected.set()
                    return

        async def replay():
            if body:
                return body.pop(0)
            await disconnected.wait()
            return {"type": "http.disconnect"}

        monitor = asyncio.create_task(watch_disconnect())
        ticket = object()
        acquired = False
        token = current_budget.set(budget)
        try:
            with self.lock:
                if self.active < settings.MAX_ACTIVE_REQUESTS and not self.queue:
                    self.active += 1
                    acquired = True
                elif len(self.queue) < settings.MAX_QUEUED_REQUESTS:
                    self.queue.append(ticket)
                else:
                    ticket = None
            if ticket is None:
                return await self.reject(scope, replay, send, "server_busy", "The server is busy. Please try again in a few seconds.")

            queue_deadline = time.monotonic() + settings.QUEUE_WAIT_SECONDS
            while not acquired:
                budget.remaining()
                if time.monotonic() >= queue_deadline:
                    return await self.reject(scope, replay, send, "server_busy", "The calculation queue is full. Please try again shortly.")
                with self.lock:
                    if self.queue and self.queue[0] is ticket and self.active < settings.MAX_ACTIVE_REQUESTS:
                        self.queue.popleft()
                        self.active += 1
                        acquired = True
                if not acquired:
                    await asyncio.sleep(0.05)

            budget.remaining()
            await self.app(scope, replay, send)
        except RequestStopped as error:
            if not error.cancelled:
                await self.reject(scope, replay, send, "request_timeout", "The request took too long and was stopped. Try a simpler problem.")
        finally:
            budget.cancelled.set()
            current_budget.reset(token)
            monitor.cancel()
            with self.lock:
                if acquired:
                    self.active -= 1
                if ticket in self.queue:
                    self.queue.remove(ticket)
            with suppress(asyncio.CancelledError):
                await monitor
